import re
import unicodedata
from typing import Annotated

from pydantic import AfterValidator

class TextSanitizer:
    # teks disimpan apa adanya tanpa di-escape, markup ditolak dan escaping dilakukan saat output
    # "<" yang langsung diikuti huruf, !, / atau ? dibaca browser sebagai awal tag
    TAG = re.compile(r"<[a-zA-Z!/?]")
    BLANK_LINES = re.compile(r"\n{3,}")

    @classmethod
    def single_line(cls, value: str) -> str:
        return cls._reject_tag(" ".join(cls._clean(value).split()))

    @classmethod
    def multi_line(cls, value: str) -> str:
        lines = (" ".join(line.split()) for line in cls._clean(value).splitlines())
        # paling banyak satu baris kosong di antara paragraf
        return cls._reject_tag(cls.BLANK_LINES.sub("\n\n", "\n".join(lines)).strip())

    @staticmethod
    def _clean(value: str) -> str:
        # NFC lalu buang karakter kategori C (kontrol, zero width, pembalik arah)
        value = unicodedata.normalize("NFC", value)
        return "".join(c for c in value if c.isspace() or unicodedata.category(c)[0] != "C")

    @classmethod
    def _reject_tag(cls, value: str) -> str:
        if cls.TAG.search(value):
            raise ValueError("Tidak boleh memuat tag HTML")
        return value

# panjang ditulis di schema, misalnya Annotated[SingleLineText, Field(min_length=3, max_length=60)],
# dan dicek sesudah teks dibersihkan
SingleLineText = Annotated[str, AfterValidator(TextSanitizer.single_line)]
MultiLineText = Annotated[str, AfterValidator(TextSanitizer.multi_line)]
