import sys
from collections.abc import Callable

from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.core.database import database
from app.seeders.base import DEMO_PASSWORD
from app.seeders.database_seeder import DatabaseSeeder

class SeedCommand:
    # python -m app.seeders [--yes], seluruh isi database diganti data demo
    LOCAL_HOSTS = frozenset({None, "", "localhost", "127.0.0.1", "::1"})

    def __init__(self, config: Settings, session_factory: Callable[[], Session]):
        self.config = config
        self.session_factory = session_factory

    def run(self, args: list[str]) -> int:
        url = make_url(self.config.database_url)
        print(f"Database tujuan: {url.render_as_string(hide_password=True)}")
        # seeder mengosongkan semua tabel, database di luar laptop (misalnya Neon) wajib --yes
        if url.host not in self.LOCAL_HOSTS and "--yes" not in args:
            print("Database tujuan bukan lokal dan semua isinya akan dihapus.")
            print("Ulangi dengan --yes bila memang disengaja.")
            return 1
        with self.session_factory() as db:
            counts = DatabaseSeeder(db).run()
        for table, count in counts.items():
            print(f"  {table:<10} {count}")
        print(f"Password semua akun demo: {DEMO_PASSWORD}")
        return 0

if __name__ == "__main__":
    sys.exit(SeedCommand(settings, database.session_factory).run(sys.argv[1:]))
