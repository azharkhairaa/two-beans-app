from datetime import date, datetime
from zoneinfo import ZoneInfo

class Clock:
    # waktu disimpan UTC, "hari ini" untuk aturan tanggal dan ringkasan dihitung dalam WIB
    ZONE = ZoneInfo("Asia/Jakarta")

    @classmethod
    def now(cls) -> datetime:
        return datetime.now(cls.ZONE)

    @classmethod
    def today(cls) -> date:
        return cls.now().date()
