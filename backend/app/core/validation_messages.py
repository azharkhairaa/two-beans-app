from collections.abc import Sequence
from typing import Any

class ValidationMessages:
    # pesan bawaan Pydantic di-mapping, pesan validator kustom dipakai apa adanya
    TEMPLATES = {
        "missing": "Wajib diisi",
        "extra_forbidden": "Field tidak dikenal",
        "json_invalid": "Body bukan JSON yang valid",
        "string_type": "Harus berupa teks",
        "string_too_short": "Minimal {min_length} karakter",
        "string_too_long": "Maksimal {max_length} karakter",
        "string_pattern_mismatch": "Format tidak valid",
        "int_type": "Harus bilangan bulat",
        "int_parsing": "Harus bilangan bulat",
        "int_from_float": "Harus bilangan bulat",
        "bool_type": "Harus true atau false",
        "bool_parsing": "Harus true atau false",
        "greater_than": "Harus lebih dari {gt}",
        "greater_than_equal": "Minimal {ge}",
        "less_than": "Harus kurang dari {lt}",
        "less_than_equal": "Maksimal {le}",
        "literal_error": "Pilihan tidak valid",
        "enum": "Pilihan tidak valid",
        "date_type": "Format tanggal harus YYYY-MM-DD",
        "date_parsing": "Format tanggal harus YYYY-MM-DD",
        "date_from_datetime_parsing": "Format tanggal harus YYYY-MM-DD",
        "date_from_datetime_inexact": "Format tanggal harus YYYY-MM-DD",
        "datetime_type": "Format waktu tidak valid",
        "datetime_parsing": "Format waktu tidak valid",
        "list_type": "Harus berupa daftar",
        "dict_type": "Harus berupa objek",
        "model_type": "Harus berupa objek",
        "model_attributes_type": "Harus berupa objek",
    }
    FALLBACK = "Nilai tidak valid"
    SOURCES = ("body", "query", "path", "header", "cookie")

    def translate(self, errors: Sequence[dict[str, Any]]) -> dict[str, str]:
        result: dict[str, str] = {}
        for error in errors:
            # satu pesan per field, yang pertama paling relevan
            result.setdefault(self.field(error), self.message(error))
        return result

    def field(self, error: dict[str, Any]) -> str:
        loc = list(error.get("loc", ()))
        if error["type"] == "json_invalid":
            return "body"
        if len(loc) > 1 and loc[0] in self.SOURCES:
            loc = loc[1:]
        return ".".join(str(part) for part in loc) or "body"

    def message(self, error: dict[str, Any]) -> str:
        kind, ctx = error["type"], error.get("ctx") or {}
        if kind == "value_error":
            # ValueError dari validator kustom membawa pesan, tanpa itu berarti email
            custom = ctx.get("error")
            return str(custom) if isinstance(custom, Exception) else "Format email tidak valid"
        if kind in ("too_short", "too_long"):
            # Field(min_length) sesudah AfterValidator memakai tipe ini, juga untuk panjang list
            unit = "baris" if ctx.get("field_type") == "List" else "karakter"
            if kind == "too_short":
                return f"Minimal {ctx.get('min_length')} {unit}"
            return f"Maksimal {ctx.get('max_length')} {unit}"
        template = self.TEMPLATES.get(kind)
        if template is None:
            return self.FALLBACK
        try:
            return template.format(**ctx)
        except (KeyError, IndexError):
            return self.FALLBACK
