import re
from decimal import Decimal, InvalidOperation
from typing import Optional, Tuple, Dict, Any, List

BENGALI_TO_ENGLISH_DIGITS = {
    '০': '0', '১': '1', '২': '2', '৩': '3', '৪': '4',
    '৫': '5', '৬': '6', '৭': '7', '৮': '8', '৯': '9'
}

UNIT_SYNONYMS = {
    'p': 'piece',
    'pc': 'piece',
    'pcs': 'piece',
    'piece': 'piece',
    'pieces': 'piece',
    'পিস': 'piece',
    'টুকরা': 'piece',
    'dz': 'dozen',
    'doz': 'dozen',
    'dozen': 'dozen',
    'ডজন': 'dozen',
    'bx': 'box',
    'box': 'box',
    'boxes': 'box',
    'বক্স': 'box',
    'kg': 'kg',
    'কেজি': 'kg',
    'gm': 'gram',
    'g': 'gram',
    'গ্রাম': 'gram',
    'ml': 'ml',
    'মিলি': 'ml',
    'l': 'litre',
    'ltr': 'litre',
    'লিটার': 'litre',
    'pkt': 'packet',
    'packet': 'packet',
    'প্যাকেট': 'packet',
}

COMMON_ABBREVIATIONS = {
    'sun': 'Sunscreen',
    'vase': 'Vaseline',
    'voe': 'Vaseline',
    'voesam': 'Vaseline',
    'cocoa': 'Cocoa',
    'cpq': 'Cocoa',
    'cantor': 'Castor',
    'contor': 'Castor',
    'contoral': 'Castor Oil',
    'ribana': 'Ribana',
    'qihane': 'Ribana',
    'sali': 'Salicylic',
    'sxo': 'Cosrx',
    'cosrx': 'Cosrx',
    'mas': 'Mascara',
    'lip': 'Lipstick',
    'enel': 'Emeli',
    'enrelr': 'Emeli',
    'badt': 'Bath',
    'salf': 'Salt',
    'bg': 'Bioaqua',
    'h/oil': 'Hair Oil',
    'b/c': 'Brightening Cream',
    'f/wash': 'Face Wash',
    'f/w': 'Face Wash',
    'powd': 'Powder',
    'cu': 'Cucumber',
    'h0d0': 'Kado',
    's481': 'Sasi',
    'aam': 'Zafran',
}


class Normalizer:
    @staticmethod
    def bengali_to_english_digits(text: Optional[str]) -> str:
        """
        Converts Bengali numerals (০-৯) to English digits (0-9).
        Handles mixed digits e.g. '৩6০' -> '360'.
        """
        if not text:
            return ""
        result = []
        for char in str(text):
            result.append(BENGALI_TO_ENGLISH_DIGITS.get(char, char))
        return "".join(result)

    @staticmethod
    def clean_amount(text: Optional[str]) -> Optional[Decimal]:
        """
        Strips '/-', '৳', 'Tk', 'Tk.', '=', commas, and returns Decimal.
        e.g. '৩৫৫০/-' -> 3550, '৳ ১,০৫০/-' -> 1050.
        """
        if not text:
            return None
        s = Normalizer.bengali_to_english_digits(str(text))
        s = re.sub(r'[/=\-\–৳,\s]', '', s)
        s = re.sub(r'(?i)tk\.?', '', s)
        match = re.search(r'\d+(\.\d+)?', s)
        if match:
            try:
                return Decimal(match.group(0))
            except InvalidOperation:
                return None
        return None

    @staticmethod
    def normalize_unit(unit_str: Optional[str]) -> str:
        """
        Normalizes unit shorthand (p, pc, পিস, dz) to canonical form.
        Defaults to 'piece' if unrecognized.
        """
        if not unit_str:
            return "piece"
        clean = unit_str.strip().lower()
        clean = re.sub(r'^\d+', '', clean).strip()
        return UNIT_SYNONYMS.get(clean, "piece")

    @staticmethod
    def extract_size_and_unit(text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extracts size number and unit from text like 'Sun 625ml' or 'Vase 50ml'.
        """
        if not text:
            return None, None
        s = Normalizer.bengali_to_english_digits(text)
        pattern = r'(?i)\b(\d+(?:\.\d+)?)\s*(ml|l|ltr|g|gm|kg|pc|pcs|box|oz)\b'
        match = re.search(pattern, s)
        if match:
            size_val = match.group(1)
            raw_unit = match.group(2).lower()
            return size_val, UNIT_SYNONYMS.get(raw_unit, raw_unit)
        return None, None

    @staticmethod
    def extract_variant_code(text: str) -> Optional[str]:
        """
        Extracts circled or parenthesized variant codes like (SH), (928), (13), (J), (F).
        """
        if not text:
            return None
        matches = re.findall(r'\(([^)]+)\)', text)
        if matches:
            for m in matches:
                clean_m = m.strip()
                if not re.match(r'^\d+\s*(ml|g|gm|kg|oz)$', clean_m, re.I):
                    return clean_m
        return None

    @staticmethod
    def expand_abbreviations(text: str, supplier_abbrevs: Optional[Dict[str, str]] = None) -> str:
        """
        Expands abbreviations using supplier-scoped mappings first, then general cosmetics abbreviations.
        Handles punctuation, parentheses, and sub-tokens.
        """
        if not text:
            return ""
        mapping = {}
        for k, v in COMMON_ABBREVIATIONS.items():
            mapping[k.lower()] = v
        if supplier_abbrevs:
            for k, v in supplier_abbrevs.items():
                mapping[k.lower()] = v

        # Normalize OCR confusions for abbreviation lookup
        def replace_token(tok: str) -> str:
            clean = tok.lower()
            if clean in mapping:
                return mapping[clean]
            # Strip trailing digits e.g. voesam6 -> voesam, cpq0 -> cpq
            clean_alpha = re.sub(r'\d+$', '', clean)
            if clean_alpha in mapping:
                return mapping[clean_alpha]
            # Try with 0->o replacement e.g. b0b -> bob
            clean_o = clean.replace('0', 'o')
            if clean_o in mapping:
                return mapping[clean_o]
            return tok

        # Tokenize preserving spaces and punctuation
        tokens = re.split(r'([^\w]+)', text)
        expanded = [replace_token(t) for t in tokens]
        return "".join(expanded)

    @classmethod
    def parse_raw_line_segments(cls, raw_text: str) -> Tuple[str, Optional[str], Optional[str], Optional[str]]:
        """
        Splits a raw line into (item_text, qty_str, unit_str, price_str)
        Handles delimiters like '-', 'x', and Bengali/English digits.
        e.g. 'Sun 625ml (SH) - ১P - ১০৫০/-' -> ('Sun 625ml (SH)', '১', 'P', '১০৫০/-')
        """
        s = raw_text.strip()
        segments = [seg.strip() for seg in re.split(r'[-–—]', s) if seg.strip()]

        if len(segments) >= 3:
            name_part = segments[0]
            middle_part = segments[1]
            price_part = segments[2]
            
            # Middle part usually has qty + unit e.g. '১P', '1 pc', '১ পিস'
            qty_match = re.search(r'([\d০-৯]+(?:\.[\d০-৯]+)?)\s*([a-zA-Z\u0980-\u09FF]*)', middle_part)
            if qty_match:
                qty_str = qty_match.group(1)
                unit_str = qty_match.group(2)
            else:
                qty_str = "1"
                unit_str = middle_part
            return name_part, qty_str, unit_str, price_part

        elif len(segments) == 2:
            name_part = segments[0]
            # Check if second part has price or qty x price
            sub = segments[1]
            if re.search(r'[\d০-৯]+', sub):
                return name_part, "1", "piece", sub
            return name_part, None, None, None

        return s, None, None, None

    @classmethod
    def normalize_line(
        cls,
        raw_text: str,
        parsed_name: Optional[str] = None,
        parsed_variant: Optional[str] = None,
        raw_qty: Optional[Any] = None,
        raw_unit: Optional[str] = None,
        raw_unit_price: Optional[Any] = None,
        raw_line_total: Optional[Any] = None,
        supplier_abbrevs: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Performs full deterministic normalization on a line item.
        """
        flags: List[str] = []

        # If raw_qty or raw_unit_price not provided, parse segments from raw_text
        if raw_qty is None or raw_unit_price is None:
            extracted_name, ext_qty, ext_unit, ext_price = cls.parse_raw_line_segments(raw_text)
            if raw_qty is None and ext_qty:
                raw_qty = ext_qty
            if raw_unit is None and ext_unit:
                raw_unit = ext_unit
            if raw_unit_price is None and ext_price:
                raw_unit_price = ext_price
            if parsed_name is None and extracted_name:
                parsed_name = extracted_name

        name_candidate = parsed_name or raw_text
        expanded_name = cls.expand_abbreviations(name_candidate, supplier_abbrevs)

        size_val, size_unit = cls.extract_size_and_unit(expanded_name)
        extracted_variant = cls.extract_variant_code(raw_text) or parsed_variant

        qty_val = Decimal("1.00")
        if raw_qty is not None:
            clean_q = cls.clean_amount(str(raw_qty))
            if clean_q is not None and clean_q > 0:
                qty_val = clean_q
            else:
                flags.append("MISSING_QTY_DEFAULTED_1")
        else:
            flags.append("MISSING_QTY_DEFAULTED_1")

        unit_val = cls.normalize_unit(raw_unit)

        unit_price_val = cls.clean_amount(str(raw_unit_price)) if raw_unit_price is not None else None
        line_total_val = cls.clean_amount(str(raw_line_total)) if raw_line_total is not None else unit_price_val

        return {
            "parsed_name": expanded_name,
            "parsed_variant": extracted_variant,
            "parsed_qty": qty_val,
            "parsed_unit": unit_val,
            "parsed_unit_price": unit_price_val,
            "parsed_line_total": line_total_val,
            "size_value": size_val,
            "size_unit": size_unit,
            "flags": flags,
        }
