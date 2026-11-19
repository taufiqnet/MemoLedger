import random
from typing import List, Dict, Any

BENGALI_DIGIT_MAP = {'0': '০', '1': '১', '2': '২', '3': '৩', '4': '৪', '5': '৫', '6': '৬', '7': '৭', '8': '৮', '9': '৯'}

SPELLING_VARIATIONS = {
    "Castor": ["Cantor", "Caster", "Castor", "Kastor"],
    "Vaseline": ["Vase", "Vaslin", "Vaseline"],
    "Sunscreen": ["Sun", "Sun scren", "Sunscreen"],
    "Salicylic": ["Sali", "Salicyl", "Salicylic"],
    "Mascara": ["Mas", "Mascara"],
}

UNIT_VARIATIONS = ["P", "pc", "pcs", "পিস", "টুকরা"]


class SyntheticVariationGenerator:
    @staticmethod
    def to_bengali_digits(number_str: str) -> str:
        return "".join(BENGALI_DIGIT_MAP.get(c, c) for c in str(number_str))

    @staticmethod
    def to_mixed_digits(number_str: str) -> str:
        res = []
        for c in str(number_str):
            if c in BENGALI_DIGIT_MAP and random.random() > 0.5:
                res.append(BENGALI_DIGIT_MAP[c])
            else:
                res.append(c)
        return "".join(res)

    @classmethod
    def generate_variations(cls, count: int = 50) -> List[Dict[str, Any]]:
        samples = []
        base_items = [
            {"name": "Sunscreen", "size": "625ml", "variant": "(SH)", "qty": 1, "price": 1050},
            {"name": "Vaseline", "size": "50ml", "variant": "(J) Co", "qty": 1, "price": 150},
            {"name": "Castor oil", "size": "200ml", "variant": "", "qty": 1, "price": 550},
            {"name": "Bath Salt", "size": "", "variant": "", "qty": 1, "price": 150},
            {"name": "W7 Eye", "size": "", "variant": "", "qty": 1, "price": 360},
            {"name": "Cosrx Sali", "size": "150ml", "variant": "(F)", "qty": 1, "price": 900},
        ]

        for i in range(count):
            item = random.choice(base_items)
            name_base = item["name"].split()[0]
            spelling_candidates = SPELLING_VARIATIONS.get(name_base, [name_base])
            chosen_name = random.choice(spelling_candidates)
            if len(item["name"].split()) > 1:
                chosen_name += " " + " ".join(item["name"].split()[1:])

            unit_cand = random.choice(UNIT_VARIATIONS)
            qty_val = str(item["qty"])
            price_val = str(item["price"])

            # Script style
            style = random.choice(["bn", "en", "mixed"])
            if style == "bn":
                qty_str = cls.to_bengali_digits(qty_val)
                price_str = cls.to_bengali_digits(price_val)
            elif style == "mixed":
                qty_str = cls.to_bengali_digits(qty_val)
                price_str = cls.to_mixed_digits(price_val)
            else:
                qty_str = qty_val
                price_str = price_val

            raw_line = f"{chosen_name} {item['size']} {item['variant']}".strip()
            raw_line += f" - {qty_str}{unit_cand} - {price_str}/-"

            samples.append({
                "synthetic_id": f"syn_{i+1}",
                "raw_text": raw_line,
                "style": style,
                "expected_name_keyword": name_base.lower(),
                "expected_price": float(item["price"]),
                "expected_qty": float(item["qty"]),
            })
        return samples
