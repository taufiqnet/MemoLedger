import uuid
from decimal import Decimal
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.models.product import Product, ProductVariant, ProductAlias
from app.models.stock import PriceHistory
from app.services.matching.embeddings import vector_embedder


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
    ) -> Dict[str, Any]:
        """
        Hybrid resolver combining:
        1. Supplier-scoped aliases
        2. Vector embedding similarity (pgvector / multilingual)
        3. Trigram similarity
        4. Strict size agreement & mismatch penalties
        5. Historical supplier price proximity
        """
        # Step 1: Check Supplier-scoped Product Alias first
        if supplier_id and parsed_name:
            alias = db.query(ProductAlias).filter(
                ProductAlias.tenant_id == tenant_id,
                ProductAlias.supplier_id == supplier_id,
                ProductAlias.alias_text.ilike(parsed_name.strip())
            ).first()
            if alias:
                variant = db.query(ProductVariant).filter(ProductVariant.id == alias.product_variant_id).first()
                if variant:
                    return {
                        "matched_variant_id": str(variant.id),
                        "matched_product_name": f"{variant.product.name} ({variant.size_value or ''}{variant.size_unit or ''})",
                        "match_confidence": 0.98,
                        "status": "AUTO_MATCHED",
                        "suggestions": [],
                        "flags": ["MATCHED_VIA_SUPPLIER_ALIAS"]
                    }

        # Step 2: Query candidate variants for tenant
        candidates = db.query(ProductVariant).join(Product).filter(
            Product.tenant_id == tenant_id
        ).all()

        if not candidates:
            return {
                "matched_variant_id": None,
                "matched_product_name": None,
                "match_confidence": 0.0,
                "status": "MANUAL_ENTRY",
                "suggestions": [],
                "flags": ["NO_PRODUCTS_IN_TENANT_CATALOG"]
            }

        query_emb = vector_embedder.embed_text(parsed_name)
        scored_candidates: List[Tuple[float, ProductVariant]] = []

        for candidate in candidates:
            cand_name = candidate.product.name
            cand_brand = candidate.product.brand or ""
            full_cand_text = f"{cand_brand} {cand_name}".strip()

            # Trigram similarity on name
            trigram_score = max(
                compute_trigram_similarity(parsed_name, cand_name),
                compute_trigram_similarity(parsed_name, full_cand_text)
            )

            # Vector cosine similarity
            if candidate.embedding:
                cand_emb = candidate.embedding if isinstance(candidate.embedding, list) else list(candidate.embedding)
            else:
                cand_emb = vector_embedder.embed_text(full_cand_text)
            vec_score = vector_embedder.cosine_similarity(query_emb, cand_emb)

            # Combined base text similarity
            text_score = (0.5 * trigram_score) + (0.5 * vec_score)

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
                "product_name": f"{c.product.name} ({c.size_value or ''}{c.size_unit or ''} {c.variant_code or ''})".strip(),
                "brand": c.product.brand,
                "score": round(s, 3),
                "cost_price": float(c.cost_price)
            }
            for s, c in scored_candidates[:3]
        ]

        # Decision Triage
        if best_score >= 0.88:
            return {
                "matched_variant_id": str(best_cand.id),
                "matched_product_name": top_suggestions[0]["product_name"],
                "match_confidence": round(best_score, 3),
                "status": "AUTO_MATCHED",
                "suggestions": top_suggestions,
                "flags": []
            }
        elif best_score >= 0.55:
            return {
                "matched_variant_id": str(best_cand.id),
                "matched_product_name": top_suggestions[0]["product_name"],
                "match_confidence": round(best_score, 3),
                "status": "SUGGESTION_NEEDED",
                "suggestions": top_suggestions,
                "flags": ["CONFIDENCE_BELOW_AUTO_MATCH_THRESHOLD"]
            }
        else:
            return {
                "matched_variant_id": None,
                "matched_product_name": None,
                "match_confidence": round(best_score, 3),
                "status": "MANUAL_ENTRY",
                "suggestions": top_suggestions,
                "flags": ["NO_CONFIDENT_CATALOG_MATCH"]
            }
