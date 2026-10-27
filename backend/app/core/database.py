from collections.abc import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

class Database:
    # engine dan session factory SQLAlchemy untuk satu URL database

    def __init__(self, url: str, serverless: bool = False):
        # tiap instance function Vercel punya pool sendiri, koneksi ke Neon dibuat seminimal mungkin
        pool = {"pool_size": 1, "max_overflow": 2} if serverless else {}
        self.engine = create_engine(
            url, pool_pre_ping=True, connect_args={"connect_timeout": 10}, **pool
        )
        self.session_factory = sessionmaker(bind=self.engine, autoflush=False)

    def session(self) -> Iterator[Session]:
        with self.session_factory() as session:
            yield session

    @staticmethod
    def is_connected(session: Session) -> bool:
        try:
            session.execute(text("SELECT 1"))
        except SQLAlchemyError:
            return False
        return True

database = Database(settings.database_url, settings.serverless)

def get_db() -> Iterator[Session]:
    yield from database.session()
