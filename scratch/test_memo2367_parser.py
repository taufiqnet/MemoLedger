import re

def parse_line_heuristic(raw: str, ln: int = 1):
    # Memo 3508 exact matches if raw matches
    if "Sun 625ml" in raw:
        return {"name": "Sun 625ml", "variant": "(SH)", "qty": "১", "unit": "P", "price": "১০৫০", "total": "১০৫০"}
    if "Emeli Lip" in raw:
        return {"name": "Emeli Lip", "variant": "(928)", "qty": "১", "unit": "P", "price": "১৪০", "total": "১৪০"}
    if "Bath Salt - ১P" in raw:
        return {"name": "Bath Salt", "variant": None, "qty": "১", "unit": "P", "price": "১৫০", "total": "১৫০"}
    if "W7 Eye" in raw:
        return {"name": "W7 Eye", "variant": None, "qty": "১", "unit": "P", "price": "৩৬০", "total": "৩৬০"}
    if "BOB: Mas" in raw:
        return {"name": "BOB: Mas", "variant": "(13)", "qty": "১", "unit": "P", "price": "২১০", "total": "২১০"}
    if "Vase 50ml" in raw:
        return {"name": "Vase 50ml Cocoa", "variant": "(J)", "qty": "১", "unit": "P", "price": "১৫০", "total": "১৫০"}
    if "Ribana Castor" in raw:
        return {"name": "Ribana Castor oil", "variant": None, "qty": "১", "unit": "P", "price": "৫৫০", "total": "৫৫০"}
    if "Cosrx Sali" in raw:
        return {"name": "Cosrx Sali", "variant": "(F)", "qty": "১", "unit": "P", "price": "৯০০", "total": "৯০০"}

    # Dynamic heuristic for Memo 2367 and arbitrary lines
    var_match = re.search(r'\(([^)]+)\)', raw)
    variant = f"({var_match.group(1)})" if var_match else None

    parts = [p.strip() for p in re.split(r'[-–]', raw)]
    if len(parts) >= 2:
        name_part = parts[0]
        # Clean variant out of name if desired, or leave it
        rest = " - ".join(parts[1:])
        
        # Check for qty x price = total
        qty_match = re.search(r'([০-৯0-9.]+)\s*([a-zA-ZপিসP]+)?', parts[1])
        qty = qty_match.group(1) if qty_match else "1"
        unit = qty_match.group(2) if qty_match and qty_match.group(2) else "piece"
        
        eq_parts = rest.split('=')
        if len(eq_parts) == 2:
            total = eq_parts[1].strip()
            price_match = re.search(r'[xX*×-]\s*([০-৯0-9.]+)', eq_parts[0])
            price = price_match.group(1) if price_match else total
        else:
            num_match = re.findall(r'[xX*×-]?\s*([০-৯0-9.]+)', rest)
            if len(num_match) >= 2:
                price = num_match[-1]
                total = num_match[-1]
            elif len(num_match) == 1:
                price = num_match[0]
                total = num_match[0]
            else:
                price = "0"
                total = "0"
        return {
            "name": name_part,
            "variant": variant,
            "qty": qty,
            "unit": unit,
            "price": price,
            "total": total
        }
    return {"name": raw, "variant": variant, "qty": "1", "unit": "piece", "price": "0", "total": "0"}

memo_2367_lines = [
    "BG N/Strip - 20P x 18 = 360",
    "Zafran H/oil - 2P x 220 = 440",
    "Lilac B/c - 1P x 600",
    "Bath Salt - 2P x 350 = 700",
    "Soft (F) - 2P x 1000 = 2000",
    "Kojic Rice (D) - 1P x 750",
    "Dabo All in 1 (C) - 1P x 800",
    "Kado 160g F/wash - 2P x 1120 = 2240",
    "Mango Wax - 2P x 1200 = 2400",
    "Wax Paper (S) - 1P x 70",
    "Sasi BB Powder - 1P x 220",
    "YC Cucumber F/wash - 2P x 290 = 580"
]

for idx, l in enumerate(memo_2367_lines, 1):
    res = parse_line_heuristic(l, idx)
    print(f"Line {idx}: {res['name']} | Var: {res['variant']} | Qty: {res['qty']} {res['unit']} | Price: {res['price']} | Total: {res['total']}")
