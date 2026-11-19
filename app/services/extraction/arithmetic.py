from decimal import Decimal
from typing import List, Tuple, Optional, Dict, Any


class ArithmeticReconciler:
    @staticmethod
    def reconcile_line(
        qty: Decimal,
        unit_price: Optional[Decimal],
        line_total: Optional[Decimal],
        typical_price_range: Optional[Dict[str, float]] = None,
    ) -> Tuple[Decimal, Decimal, List[str]]:
        """
        Reconciles (unit_price, line_total) using qty * unit_price = line_total.
        Returns: (final_unit_price, final_line_total, flags)
        """
        flags: List[str] = []

        # If both are present, verify
        if unit_price is not None and line_total is not None:
            expected_total = qty * unit_price
            diff = abs(expected_total - line_total)
            if diff > Decimal("0.05"):
                flags.append(f"LINE_ARITHMETIC_MISMATCH ({qty} x {unit_price} = {expected_total} != {line_total})")
            return unit_price, line_total, flags

        # If only unit price is present
        if unit_price is not None and line_total is None:
            calculated_total = qty * unit_price
            return unit_price, calculated_total, flags

        # If only line total is present
        if unit_price is None and line_total is not None:
            if qty == 1:
                return line_total, line_total, flags
            elif qty > 1:
                calculated_unit = line_total / qty
                return calculated_unit, line_total, flags
            else:
                return line_total, line_total, flags

        # Neither is present
        flags.append("MISSING_PRICE_AND_TOTAL")
        return Decimal("0.00"), Decimal("0.00"), flags

    @classmethod
    def reconcile_memo(
        cls,
        lines: List[Dict[str, Any]],
        written_total: Optional[Decimal] = None
    ) -> Tuple[List[Dict[str, Any]], Decimal, bool, List[str]]:
        """
        Reconciles all lines in a memo and verifies the sum against written_total.
        Returns: (reconciled_lines, calculated_sum, total_mismatch_flag, global_flags)
        """
        reconciled_lines: List[Dict[str, Any]] = []
        calculated_sum = Decimal("0.00")
        global_flags: List[str] = []

        for line in lines:
            qty = Decimal(str(line.get("parsed_qty", 1.0)))
            up = Decimal(str(line["parsed_unit_price"])) if line.get("parsed_unit_price") is not None else None
            lt = Decimal(str(line["parsed_line_total"])) if line.get("parsed_line_total") is not None else None

            final_up, final_lt, flags = cls.reconcile_line(qty, up, lt)
            
            line_flags = list(line.get("flags", [])) + flags
            reconciled_line = dict(line)
            reconciled_line["parsed_unit_price"] = final_up
            reconciled_line["parsed_line_total"] = final_lt
            reconciled_line["flags"] = line_flags
            
            calculated_sum += final_lt
            reconciled_lines.append(reconciled_line)

        total_mismatch = False
        if written_total is not None and written_total > 0:
            diff = abs(calculated_sum - written_total)
            if diff > Decimal("0.50"):
                total_mismatch = True
                global_flags.append(
                    f"TOTAL_MISMATCH (Line items sum to ৳{calculated_sum:.2f} but written total is ৳{written_total:.2f})"
                )

        return reconciled_lines, calculated_sum, total_mismatch, global_flags
