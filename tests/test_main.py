import os
import tempfile

# Harus diset SEBELUM app diimpor, supaya test memakai SQLite sementara.
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def make_payload(**overrides):
    payload = {
        "account_id": "ACC-001",
        "amount": "150000.50",
        "type": "credit",
        "description": "Top up",
    }
    payload.update(overrides)
    return payload


def test_health_and_metrics():
    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

        r = client.get("/metrics")
        assert r.status_code == 200
        assert "http_requests_total" in r.text


def test_crud_flow():
    with TestClient(app) as client:
        r = client.post("/transactions", json=make_payload())
        assert r.status_code == 201
        trx_id = r.json()["id"]

        r = client.get(f"/transactions/{trx_id}")
        assert r.status_code == 200
        assert r.json()["account_id"] == "ACC-001"

        r = client.get("/transactions")
        assert r.status_code == 200
        assert any(t["id"] == trx_id for t in r.json())

        r = client.put(
            f"/transactions/{trx_id}",
            json=make_payload(type="debit", description="Bayar"),
        )
        assert r.status_code == 200
        assert r.json()["type"] == "debit"

        r = client.delete(f"/transactions/{trx_id}")
        assert r.status_code == 204

        r = client.get(f"/transactions/{trx_id}")
        assert r.status_code == 404


def test_validation_rejects_bad_input():
    with TestClient(app) as client:
        assert client.post("/transactions", json=make_payload(amount="-5")).status_code == 422
        assert client.post("/transactions", json=make_payload(type="transfer")).status_code == 422
