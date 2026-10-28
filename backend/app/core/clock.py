from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime
from zoneinfo import ZoneInfo

class Clock:
    # waktu disimpan UTC, "hari ini" untuk aturan tanggal dan ringkasan dihitung dalam WIB
    ZONE = ZoneInfo("Asia/Jakarta")
    _frozen: datetime | None = None

    @classmethod
    def now(cls) -> datetime:
        if cls._frozen is not None:
            return cls._frozen
        return datetime.now(cls.ZONE)

    @classmethod
    def today(cls) -> date:
        return cls.now().date()

    @classmethod
    @contextmanager
    def at(cls, moment: datetime) -> Iterator[None]:
        previous = cls._frozen
        cls._frozen = (
            moment.astimezone(cls.ZONE)
            if moment.tzinfo
            else moment.replace(tzinfo=cls.ZONE)
        )
        try:
            yield
        finally:
            cls._frozen = previous
