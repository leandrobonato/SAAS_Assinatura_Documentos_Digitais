from datetime import datetime, timedelta

from pypdf import PdfReader
import io

from app import models
from .helpers import make_sample_pdf, make_signature_data_url


def _register(client, email="owner@example.com", name="Dona Empresa"):
    r = client.post("/auth/register", json={"name": name, "email": email, "password": "senha123"})
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _upload_document(client, token, title="Contrato de teste"):
    files = {"file": ("contrato.pdf", make_sample_pdf(2), "application/pdf")}
    data = {"title": title}
    r = client.post("/documents", headers=_auth_headers(token), files=files, data=data)
    assert r.status_code == 201, r.text
    return r.json()


def test_full_signing_flow(client):
    owner_token = _register(client, email="owner1@example.com")
    document = _upload_document(client, owner_token)
    doc_id = document["id"]

    r = client.post(
        f"/documents/{doc_id}/signers",
        headers=_auth_headers(owner_token),
        json={"name": "João Signatário", "email": "joao@example.com"},
    )
    assert r.status_code == 201, r.text
    signer = r.json()

    r = client.put(
        f"/documents/{doc_id}/fields",
        headers=_auth_headers(owner_token),
        json={"fields": [{"signer_id": signer["id"], "page_number": 0, "x": 0.1, "y": 0.8, "width": 0.2, "height": 0.08}]},
    )
    assert r.status_code == 200, r.text

    r = client.post(f"/documents/{doc_id}/send", headers=_auth_headers(owner_token))
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "sent"

    # Emails are mocked to disk; grab the signer's real token straight from the DB.
    from app.database import SessionLocal
    db = SessionLocal()
    signer_row = db.query(models.Signer).filter(models.Signer.id == signer["id"]).first()
    signer_token = signer_row.token
    db.close()

    r = client.get(f"/public/sign/{signer_token}")
    assert r.status_code == 200, r.text
    view = r.json()
    assert view["signer_status"] == "viewed"
    assert len(view["fields"]) == 1
    assert view["total_pages"] == 2

    r = client.post(
        f"/public/sign/{signer_token}",
        json={"signature_image": make_signature_data_url(), "typed_name": "João Signatário"},
    )
    assert r.status_code == 200, r.text
    completed_doc = r.json()
    assert completed_doc["status"] == "completed"

    r = client.get(f"/documents/{doc_id}", headers=_auth_headers(owner_token))
    assert r.status_code == 200
    body = r.json()
    assert body["final_hash"] is not None
    assert body["signers"][0]["status"] == "signed"

    r = client.get(f"/documents/{doc_id}/final.pdf", headers=_auth_headers(owner_token))
    assert r.status_code == 200
    assert r.content.startswith(b"%PDF")
    reader = PdfReader(io.BytesIO(r.content))
    assert len(reader.pages) == 3  # 2 original pages + 1 certificate page

    r = client.get(f"/documents/{doc_id}/audit", headers=_auth_headers(owner_token))
    assert r.status_code == 200
    events = [e["event"] for e in r.json()]
    assert events == ["sent", "viewed", "signed", "completed"]


def test_invalid_signing_token_returns_404(client):
    r = client.get("/public/sign/token-que-nao-existe")
    assert r.status_code == 404


def test_free_plan_rejects_more_than_one_signer(client):
    token = _register(client, email="freeplan@example.com")
    document = _upload_document(client, token)
    doc_id = document["id"]

    for email in ["a@example.com", "b@example.com"]:
        r = client.post(
            f"/documents/{doc_id}/signers",
            headers=_auth_headers(token),
            json={"name": email, "email": email},
        )
        assert r.status_code == 201

    signers = client.get(f"/documents/{doc_id}", headers=_auth_headers(token)).json()["signers"]
    fields = [
        {"signer_id": s["id"], "page_number": 0, "x": 0.1, "y": 0.8, "width": 0.2, "height": 0.08}
        for s in signers
    ]
    client.put(f"/documents/{doc_id}/fields", headers=_auth_headers(token), json={"fields": fields})

    r = client.post(f"/documents/{doc_id}/send", headers=_auth_headers(token))
    assert r.status_code == 402
    assert "1 signatário" in r.json()["detail"]


def test_free_plan_monthly_limit(client):
    token = _register(client, email="quota@example.com")

    for i in range(5):
        document = _upload_document(client, token, title=f"Doc {i}")
        doc_id = document["id"]
        r = client.post(
            f"/documents/{doc_id}/signers",
            headers=_auth_headers(token),
            json={"name": "Signer", "email": f"signer{i}@example.com"},
        )
        signer_id = r.json()["id"]
        client.put(
            f"/documents/{doc_id}/fields",
            headers=_auth_headers(token),
            json={"fields": [{"signer_id": signer_id, "page_number": 0, "x": 0.1, "y": 0.8, "width": 0.2, "height": 0.08}]},
        )
        r = client.post(f"/documents/{doc_id}/send", headers=_auth_headers(token))
        assert r.status_code == 200, r.text

    document = _upload_document(client, token, title="Doc extra")
    doc_id = document["id"]
    r = client.post(
        f"/documents/{doc_id}/signers",
        headers=_auth_headers(token),
        json={"name": "Signer", "email": "extra@example.com"},
    )
    signer_id = r.json()["id"]
    client.put(
        f"/documents/{doc_id}/fields",
        headers=_auth_headers(token),
        json={"fields": [{"signer_id": signer_id, "page_number": 0, "x": 0.1, "y": 0.8, "width": 0.2, "height": 0.08}]},
    )
    r = client.post(f"/documents/{doc_id}/send", headers=_auth_headers(token))
    assert r.status_code == 402
    assert "Limite mensal" in r.json()["detail"]


def test_pro_plan_allows_batch_and_reminders(client):
    token = _register(client, email="pro@example.com")
    r = client.patch("/auth/me/plan", headers=_auth_headers(token), json={"plan": "pro"})
    assert r.status_code == 200
    assert r.json()["plan"] == "pro"

    document = _upload_document(client, token, title="Contrato em lote")
    doc_id = document["id"]

    signer_ids = []
    for email in ["c1@example.com", "c2@example.com"]:
        r = client.post(
            f"/documents/{doc_id}/signers",
            headers=_auth_headers(token),
            json={"name": email, "email": email},
        )
        signer_ids.append(r.json()["id"])

    fields = [
        {"signer_id": sid, "page_number": 0, "x": 0.1, "y": 0.8, "width": 0.2, "height": 0.08}
        for sid in signer_ids
    ]
    client.put(f"/documents/{doc_id}/fields", headers=_auth_headers(token), json={"fields": fields})

    r = client.post(f"/documents/{doc_id}/send", headers=_auth_headers(token))
    assert r.status_code == 200, r.text

    # Force the "sent 5 days ago, never reminded" state a real clock would
    # reach after `reminder_after_days`, without sleeping the test suite.
    from app.database import SessionLocal
    db = SessionLocal()
    doc_row = db.query(models.Document).filter(models.Document.id == doc_id).first()
    doc_row.sent_at = datetime.utcnow() - timedelta(days=5)
    db.add(doc_row)
    db.commit()
    db.close()

    r = client.post("/admin/run-reminders", headers=_auth_headers(token))
    assert r.status_code == 200
    assert r.json()["reminders_sent"] == 2
