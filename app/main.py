"""Transaction API: layanan CRUD transaksi sederhana.

Endpoint:
  GET    /health             -> cek aplikasi dan koneksi database
  GET    /metrics            -> metrik Prometheus
  POST   /transactions       -> buat transaksi
  GET    /transactions       -> daftar transaksi
  GET    /transactions/{id}  -> detail transaksi
  PUT    /transactions/{id}  -> ubah transaksi
  DELETE /transactions/{id}  -> hapus transaksi
"""
import os
from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Response
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import DateTime, Numeric, String, create_engine, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

# Kredensial TIDAK ditulis di kode. Nilai datang dari environment variable.
# Default sqlite hanya untuk menjalankan test tanpa database sungguhan.
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./dev.db")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    account_id: Mapped[str] = mapped_column(String(50), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    type: Mapped[str] = mapped_column(String(10))
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class TransactionIn(BaseModel):
    account_id: str = Field(min_length=1, max_length=50)
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    type: Literal["debit", "credit"]
    description: str | None = Field(default=None, max_length=255)


class TransactionOut(TransactionIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Transaction API", version="1.0.0", lifespan=lifespan)
Instrumentator().instrument(app).expose(app, include_in_schema=False)


@app.get("/health")
def health(response: Response, db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        response.status_code = 503
        return {"status": "unhealthy", "database": "down"}
    return {"status": "ok", "database": "up"}


@app.post("/transactions", response_model=TransactionOut, status_code=201)
def create_transaction(payload: TransactionIn, db: Session = Depends(get_db)):
    trx = Transaction(**payload.model_dump())
    db.add(trx)
    db.commit()
    db.refresh(trx)
    return trx


@app.get("/transactions", response_model=list[TransactionOut])
def list_transactions(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    limit = min(limit, 200)
    return db.query(Transaction).order_by(Transaction.id).offset(skip).limit(limit).all()


@app.get("/transactions/{trx_id}", response_model=TransactionOut)
def get_transaction(trx_id: int, db: Session = Depends(get_db)):
    trx = db.get(Transaction, trx_id)
    if trx is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return trx


@app.put("/transactions/{trx_id}", response_model=TransactionOut)
def update_transaction(trx_id: int, payload: TransactionIn, db: Session = Depends(get_db)):
    trx = db.get(Transaction, trx_id)
    if trx is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    for key, value in payload.model_dump().items():
        setattr(trx, key, value)
    db.commit()
    db.refresh(trx)
    return trx


@app.delete("/transactions/{trx_id}", status_code=204)
def delete_transaction(trx_id: int, db: Session = Depends(get_db)):
    trx = db.get(Transaction, trx_id)
    if trx is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.delete(trx)
    db.commit()
    return Response(status_code=204)
