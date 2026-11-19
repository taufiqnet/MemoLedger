import pytest
from decimal import Decimal
from app.services.extraction.normalizer import Normalizer


def test_bengali_to_english_digits():
    assert Normalizer.bengali_to_english_digits("১০৫০") == "1050"
    assert Normalizer.bengali_to_english_digits("১৫০") == "150"
    assert Normalizer.bengali_to_english_digits("৩৬০") == "360"
    assert Normalizer.bengali_to_english_digits("২১০") == "210"
    assert Normalizer.bengali_to_english_digits("৫৫০") == "550"
    assert Normalizer.bengali_to_english_digits("৯০০") == "900"
    assert Normalizer.bengali_to_english_digits("৩৫৫০") == "3550"
    # Mixed digits
    assert Normalizer.bengali_to_english_digits("৩6০") == "360"
    assert Normalizer.bengali_to_english_digits("1P x ১০৫০") == "1P x 1050"


def test_clean_monetary_amount():
    assert Normalizer.clean_amount("৩৫৫০/-") == Decimal("3550")
    assert Normalizer.clean_amount("৳ ১০৫০/-") == Decimal("1050")
    assert Normalizer.clean_amount("= ৩৫২০/-") == Decimal("3520")
    assert Normalizer.clean_amount("Tk. 150") == Decimal("150")
    assert Normalizer.clean_amount("  ৳ 550.00  ") == Decimal("550.00")
    assert Normalizer.clean_amount("N/A") is None


def test_unit_normalization():
    assert Normalizer.normalize_unit("P") == "piece"
    assert Normalizer.normalize_unit("pc") == "piece"
    assert Normalizer.normalize_unit("pcs") == "piece"
    assert Normalizer.normalize_unit("পিস") == "piece"
    assert Normalizer.normalize_unit("টুকরা") == "piece"
    assert Normalizer.normalize_unit("dz") == "dozen"
    assert Normalizer.normalize_unit("ডজন") == "dozen"
    assert Normalizer.normalize_unit("box") == "box"
    assert Normalizer.normalize_unit("বক্স") == "box"


def test_extract_size_and_unit():
    assert Normalizer.extract_size_and_unit("Sun 625ml (SH)") == ("625", "ml")
    assert Normalizer.extract_size_and_unit("Vase 50ml Cocoa") == ("50", "ml")
    assert Normalizer.extract_size_and_unit("Bath Salt 100g") == ("100", "gram")
    assert Normalizer.extract_size_and_unit("Ribana Castor oil") == (None, None)


def test_extract_variant_code():
    assert Normalizer.extract_variant_code("Sun 625ml (SH)") == "SH"
    assert Normalizer.extract_variant_code("Emeli Lip (928)") == "928"
    assert Normalizer.extract_variant_code("BOB: Mas (13)") == "13"
    assert Normalizer.extract_variant_code("Vase 50ml (J) Co") == "J"
    assert Normalizer.extract_variant_code("Cosrx Sali (F)") == "F"


def test_expand_abbreviations():
    supplier_abbrevs = {"Sun": "Sunscreen", "Vase": "Vaseline", "Cantor": "Castor"}
    expanded = Normalizer.expand_abbreviations("Sun 625ml", supplier_abbrevs)
    assert "Sunscreen" in expanded

    expanded2 = Normalizer.expand_abbreviations("Vase 50ml", supplier_abbrevs)
    assert "Vaseline" in expanded2

    expanded3 = Normalizer.expand_abbreviations("Ribana Cantor oil", supplier_abbrevs)
    assert "Castor" in expanded3
