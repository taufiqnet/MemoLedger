import pytest
from decimal import Decimal
from app.services.extraction.arithmetic import ArithmeticReconciler


def test_reconcile_single_line_exact():
    qty = Decimal("1.0")
    up = Decimal("1050.00")
    lt = Decimal("1050.00")
    final_up, final_lt, flags = ArithmeticReconciler.reconcile_line(qty, up, lt)
    assert final_up == Decimal("1050.00")
    assert final_lt == Decimal("1050.00")
    assert len(flags) == 0


def test_reconcile_single_line_missing_total():
    qty = Decimal("2.0")
    up = Decimal("150.00")
    lt = None
    final_up, final_lt, flags = ArithmeticReconciler.reconcile_line(qty, up, lt)
    assert final_up == Decimal("150.00")
    assert final_lt == Decimal("300.00")
    assert len(flags) == 0


def test_reconcile_line_mismatch_flag():
    qty = Decimal("2.0")
    up = Decimal("150.00")
    lt = Decimal("400.00")  # Mismatch (2 * 150 = 300 != 400)
    final_up, final_lt, flags = ArithmeticReconciler.reconcile_line(qty, up, lt)
    assert len(flags) > 0
    assert "LINE_ARITHMETIC_MISMATCH" in flags[0]


def test_reconcile_memo_total_match():
    lines = [
        {"parsed_qty": Decimal("1.0"), "parsed_unit_price": Decimal("1050.00"), "parsed_line_total": Decimal("1050.00")},
        {"parsed_qty": Decimal("1.0"), "parsed_unit_price": Decimal("150.00"), "parsed_line_total": Decimal("150.00")},
        {"parsed_qty": Decimal("1.0"), "parsed_unit_price": Decimal("350.00"), "parsed_line_total": Decimal("350.00")},
    ]
    written_total = Decimal("1550.00")
    r_lines, total_sum, mismatch, flags = ArithmeticReconciler.reconcile_memo(lines, written_total)
    assert total_sum == Decimal("1550.00")
    assert mismatch is False
    assert len(flags) == 0


def test_reconcile_memo_total_mismatch():
    lines = [
        {"parsed_qty": Decimal("1.0"), "parsed_unit_price": Decimal("1050.00"), "parsed_line_total": Decimal("1050.00")},
        {"parsed_qty": Decimal("1.0"), "parsed_unit_price": Decimal("500.00"), "parsed_line_total": Decimal("500.00")},
    ]
    written_total = Decimal("2000.00")  # Actual sum is 1550
    r_lines, total_sum, mismatch, flags = ArithmeticReconciler.reconcile_memo(lines, written_total)
    assert total_sum == Decimal("1550.00")
    assert mismatch is True
    assert len(flags) > 0
    assert "TOTAL_MISMATCH" in flags[0]
