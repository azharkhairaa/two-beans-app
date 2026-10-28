from pydantic import BaseModel, ConfigDict

class LokasiSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kode: str
    nama: str
    jenis: str
