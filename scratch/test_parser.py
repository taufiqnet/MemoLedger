import re

lines = [
    'BG N/Strip - 20P x 18 = 360',
    'Zafran H/oil - 2P x 220 = 440',
    'Lilac B/c - 1P x 600',
    'Bath Salt - 2P x 350 = 700',
    'Soft (F) - 2P x 1000 = 2000',
    'Kojic Rice (D) - 1P x 750',
    'Dabo All in 1 (C) - 1P x 800',
    'Kado 160g F/wash - 2P x 1120 = 2240',
    'Mango Wax - 2P x 1200 = 2400',
    'Wax Paper (S) - 1P x 70',
    'Sasi BB Powder - 1P x 220',
    'YC Cucumber F/wash - 2P x 290 = 580',
    'Sun 625ml (SH) - ১P - ১০৫০',
    'Emeli Lip (928) - ১P - ১৪০',
    'Bath Salt - ১P - ১৫০',
    'W7 Eye - ১P - ৩৬০',
    'BOB: Mas (13) - ১P - ২১০',
    'Vase 50ml (J) Co - ১P - ১৫০',
    'Ribana Castor oil - ১P - ৫৫০',
    'Cosrx Sali (F) - ১P - ৯০০'
]

def parse_line_heuristic(raw: str):
    # Extract variant in parentheses
    var_match = re.search(r'\(([^)]+)\)', raw)
    variant = f"({var_match.group(1)})" if var_match else None
    
    # Try splitting by '-' or '–'
    parts = [p.strip() for p in re.split(r'[-–]', raw)]
    if len(parts) >= 2:
        name_part = parts[0]
        # Clean variant out of name if desired, or leave it
        rest = " - ".join(parts[1:])
        
        # Check for qty x price = total
        qty_match = re.search(r'([০-৯0-9.]+)\s*([a-zA-ZপিসP]+)?', parts[1])
        qty = qty_match.group(1) if qty_match else "1"
        unit = qty_match.group(2) if qty_match and qty_match.group(2) else "piece"
        
        # Check for price / total in rest
        eq_parts = rest.split('=')
        if len(eq_parts) == 2:
            total = eq_parts[1].strip()
            # price from eq_parts[0]
            price_match = re.search(r'[xX*×-]\s*([০-৯0-9.]+)', eq_parts[0])
            price = price_match.group(1) if price_match else total
        else:
            # Maybe: 1P x 600 or 1P - 1050
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

for l in lines:
    res = parse_line_heuristic(l)
    print(f"'{l}' -> Name: '{res['name']}', Var: {res['variant']}, Qty: {res['qty']}, Unit: '{res['unit']}', Price: {res['price']}, Total: {res['total']}")
