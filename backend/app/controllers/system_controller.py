from fastapi import Depends, Response
from sqlalchemy.orm import Session

from app.core.database import Database, get_db
from app.schemas.system import HealthResponse

class SystemController:
    def health(self, response: Response, db: Session = Depends(get_db)) -> HealthResponse:
        if Database.is_connected(db):
            return HealthResponse(status="ok", database="koneksi database ok")
        # 503 monitor uptime, check API hidup tapi database tidak konek
        response.status_code = 503
        return HealthResponse(status="gangguan", database="koneksi database putus")
