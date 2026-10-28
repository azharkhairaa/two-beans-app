import pytest

from app.core.sanitize import TextSanitizer

@pytest.mark.parametrize("raw, clean", [
    ("  Kopi   Gayo  ", "Kopi Gayo"),
    ("Kopi\tGayo\nAceh", "Kopi Gayo Aceh"),
    ("Café Senja", "Café Senja"),
    ("Ko\x00pi​ Ga‮yo", "Kopi Gayo"),
    ("Harga < 50 ribu, stok <= 3", "Harga < 50 ribu, stok <= 3"),
])
def test_single_line_cleaned(raw, clean):
    assert TextSanitizer.single_line(raw) == clean

@pytest.mark.parametrize("raw", [
    "<script>alert(1)</script>",
    "<img src=x onerror=alert(1)>",
    "tebal</b>",
    "<!-- komentar -->",
    "<?xml version='1.0'?>",
])
def test_markup_rejected(raw):
    with pytest.raises(ValueError, match="tag HTML"):
        TextSanitizer.single_line(raw)
    with pytest.raises(ValueError, match="tag HTML"):
        TextSanitizer.multi_line(raw)

def test_multi_line_keeps_paragraphs():
    raw = "  Baris satu  \r\n\r\n\r\n\r\nBaris\t dua  Baris tiga\n"
    assert TextSanitizer.multi_line(raw) == "Baris satu\n\nBaris dua\nBaris tiga"
