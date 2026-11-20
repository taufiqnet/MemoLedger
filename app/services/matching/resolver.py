import uuid
from decimal import Decimal
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.models.product import Product, ProductVariant, ProductAlias
from app.models.stock import PriceHistory
from app.services.matching.embeddings import vector_embedder


import difflib
import re

def compute_trigram_similarity(str1: str, str2: str) -> float:
    """
    Computes trigram (3-gram) Dice coefficient similarity between two strings.
    Handles typos like Castor / Cantor / Caster seamlessly.
    """
    s1 = (str1 or "").lower().strip()
    s2 = (str2 or "").lower().strip()
    if not s1 or not s2:
        return 0.0
    if s1 == s2:
        return 1.0
    if len(s1) < 3 or len(s2) < 3:
        # Fallback to bigram for very short words
        grams1 = set(s1[i:i+2] for i in range(len(s1)-1))
        grams2 = set(s2[i:i+2] for i in range(len(s2)-1))
    else:
        grams1 = set(s1[i:i+3] for i in range(len(s1)-2))
        grams2 = set(s2[i:i+3] for i in range(len(s2)-2))
    
    if not grams1 or not grams2:
        return 0.0
    intersection = len(grams1 & grams2)
    return (2.0 * intersection) / (len(grams1) + len(grams2))


def compute_fuzzy_score(s1: str, s2: str) -> float:
    """
    Combines trigram, sequence matcher, and token-level fuzzy ratios with OCR digit normalization.
    """
    str1 = (s1 or "").lower().strip()
    str2 = (s2 or "").lower().strip()
    if not str1 or not str2:
        return 0.0
    if str1 == str2:
        return 1.0

    # Normalize common OCR confusions: 0->o, 1->l, 5->s, 8->b
    norm1 = str1.replace('0', 'o').replace('1', 'l').replace('5', 's').replace('8', 'b')
    norm2 = str2.replace('0', 'o').replace('1', 'l').replace('5', 's').replace('8', 'b')

    tri = compute_trigram_similarity(norm1, norm2)
    seq = difflib.SequenceMatcher(None, norm1, norm2).ratio()

    toks1 = [t for t in re.split(r'[^a-zA-Z0-9]+', norm1) if len(t) >= 2]
    toks2 = [t for t in re.split(r'[^a-zA-Z0-9]+', norm2) if len(t) >= 2]
    tok_score = 0.0
    if toks1 and toks2:
        matches = []
        for t1 in toks1:
            best_m = 0.0
            for t2 in toks2:
                if t1 == t2:
                    m = 1.0
                elif (t1 in t2 or t2 in t1) and min(len(t1), len(t2)) >= 3:
                    m = 0.85
                else:
                    m = difflib.SequenceMatcher(None, t1, t2).ratio()
                if m > best_m:
                    best_m = m
            matches.append(best_m)
        tok_score = sum(matches) / len(matches)

    return max(tri, seq, tok_score)


def _format_display_name(variant: ProductVariant) -> str:
    parts = []
    if variant.size_value:
        parts.append(f"{variant.size_value}{variant.size_unit or ''}".strip())
    if variant.variant_code:
        parts.append(variant.variant_code.strip())
    if parts:
        return f"{variant.product.name} ({' '.join(parts)})"
    return variant.product.name


class ProductResolver:
    @staticmethod
    def resolve_line(
        db: Session,
        tenant_id: uuid.UUID,
        supplier_id: Optional[uuid.UUID],
        parsed_name: str,
        parsed_variant: Optional[str] = None,
        size_value: Optional[str] = None,
        size_unit: Optional[str] = None,
        unit_price: Optional[Decimal] = None,
        excluded_variant_ids: Optional[set] = None,
    ) -> Dict[str, Any]:
        """
        Hybrid resolver combining:
        1. Supplier-scoped aliases
        2. Vector embedding similarity (pgvector / multilingual)
        3. Fuzzy and Trigram similarity on Full Name and Short Name
        4. Strict size agreement & mismatch penalties
        5. Historical supplier price proximity
        6. Exclusion of already assigned variants to prevent repeats
        """
        excluded = excluded_variant_ids or set()

        # Step 1: Check Supplier-scoped Product Alias first
        if supplier_id and parsed_name:
            alias = db.query(ProductAlias).filter(
                ProductAlias.tenant_id == tenant_id,
                ProductAlias.supplier_id == supplier_id,
                ProductAlias.alias_text.ilike(parsed_name.strip())
            ).first()
            if alias and alias.product_variant_id not in excluded:
                variant = db.query(ProductVariant).filter(ProductVariant.id == alias.product_variant_id).first()
                if variant:
                    return {
                        "matched_variant_id": str(variant.id),
                        "matched_clean_name": variant.product.name,
                        "matched_product_name": _format_display_name(variant),
                        "match_confidence": 0.98,
                        "status": "AUTO_MATCHED",
                        "suggestions": [],
                        "flags": ["MATCHED_VIA_SUPPLIER_ALIAS"]
                    }

        # Step 2: Query candidate variants for tenant (excluding already assigned)
        all_candidates = db.query(ProductVariant).join(Product).filter(
            Product.tenant_id == tenant_id
        ).all()

        candidates = [c for c in all_candidates if c.id not in excluded]

        if not candidates:
            return {
                "matched_variant_id": None,
                "matched_clean_name": "",
                "matched_product_name": "",
                "match_confidence": 0.0,
                "status": "MANUAL_ENTRY",
                "suggestions": [],
                "flags": ["NO_AVAILABLE_PRODUCTS_IN_TENANT_CATALOG"]
            }

        # If parsed_name is empty or purely noise without letters, do not match
        if not parsed_name or not re.search(r'[a-zA-Z\u0980-\u09FF]{2,}', parsed_name):
            return {
                "matched_variant_id": None,
                "matched_clean_name": "",
                "matched_product_name": "",
                "match_confidence": 0.0,
                "status": "MANUAL_ENTRY",
                "suggestions": [],
                "flags": ["EMPTY_OR_NOISY_ITEM_NAME"]
            }

        query_emb = vector_embedder.embed_text(parsed_name)
        scored_candidates: List[Tuple[float, ProductVariant]] = []

        for candidate in candidates:
            cand_name = candidate.product.name
            cand_short = candidate.product.short_name or ""
            cand_brand = candidate.product.brand or ""
            full_cand_text = f"{cand_brand} {cand_name}".strip()

            # Fuzzy + Trigram score on Full Name AND Short Name (handwritten variant)
            scores = [
                compute_fuzzy_score(parsed_name, cand_name),
                compute_fuzzy_score(parsed_name, full_cand_text)
            ]
            if cand_short:
                scores.append(compute_fuzzy_score(parsed_name, cand_short))
                scores.append(compute_fuzzy_score(parsed_name, f"{cand_brand} {cand_short}".strip()))

            base_score = max(scores)

            # Vector cosine similarity
            if candidate.embedding:
                cand_emb = candidate.embedding if isinstance(candidate.embedding, list) else list(candidate.embedding)
            else:
                cand_emb = vector_embedder.embed_text(f"{cand_name} {cand_short}".strip())
            vec_score = vector_embedder.cosine_similarity(query_emb, cand_emb)

            # Combined base text similarity
            text_score = max(base_score, (0.5 * base_score) + (0.5 * vec_score))

            # SIZE PENALTY / BONUS (Crucial requirement: different sizes NEVER merge)
            size_modifier = 0.0
            if size_value and candidate.size_value:
                clean_q_size = str(size_value).strip().lower()
                clean_c_size = str(candidate.size_value).strip().lower()
                if clean_q_size == clean_c_size:
                    size_modifier += 0.20
                else:
                    # Heavy mismatch penalty!
                    size_modifier -= 0.60
            elif size_value and not candidate.size_value:
                # Query specified a size, but variant has none
                size_modifier -= 0.15

            # VARIANT CODE BONUS / PENALTY
            variant_modifier = 0.0
            if parsed_variant and candidate.variant_code:
                pv = str(parsed_variant).strip().lower()
                cv = str(candidate.variant_code).strip().lower()
                if pv == cv or pv in cv or cv in pv:
                    variant_modifier += 0.15

            # PRICE PROXIMITY BONUS
            price_modifier = 0.0
            if unit_price and unit_price > 0 and candidate.cost_price > 0:
                cost = Decimal(str(candidate.cost_price))
                diff_pct = abs(unit_price - cost) / cost
                if diff_pct <= Decimal("0.15"):
                    price_modifier += 0.10

            final_score = text_score + size_modifier + variant_modifier + price_modifier
            final_score = max(0.0, min(1.0, final_score))
            scored_candidates.append((final_score, candidate))

        # Sort candidates descending by score
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        best_score, best_cand = scored_candidates[0]

        top_suggestions = [
            {
                "variant_id": str(c.id),
                "clean_name": c.product.name,
                "product_name": _format_display_name(c),
                "brand": c.product.brand,
                "score": round(s, 3),
                "cost_price": float(c.cost_price)
            }
            for s, c in scored_candidates[:3]
        ]

        # Decision Triage
        # If score >= 0.65: Auto-match cleanly to the full product name
        # If score < 0.65: Leave product name BLANK per user instruction, preserving price
        if best_score >= 0.65:
            return {
                "matched_variant_id": str(best_cand.id),
                "matched_clean_name": best_cand.product.name,
                "matched_product_name": top_suggestions[0]["product_name"],
                "match_confidence": round(best_score, 3),
                "status": "AUTO_MATCHED",
                "suggestions": top_suggestions,
                "flags": []
            }
        else:
            return {
                "matched_variant_id": None,
                "matched_clean_name": "",  # Blank name for unclear item
                "matched_product_name": "",
                "match_confidence": round(best_score, 3),
                "status": "MANUAL_ENTRY",
                "suggestions": top_suggestions,
                "flags": ["UNCLEAR_ITEM_NAME_BLANKED"]
            }
