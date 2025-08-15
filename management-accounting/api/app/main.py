from __future__ import annotations
import os, io, uuid, orjson
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from datetime import datetime
import csv
import pandas as pd
from .config import settings
from .db import SessionLocal
from . import models
from .parser import parse_pdf_bytes
from .security import hash_password, verify_password, set_session_cookie, require_session, require_csrf
from .worker import queue_parse

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.APP_URL],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

@app.middleware("http")
async def json_logger(request: Request, call_next):
    start = datetime.utcnow()
    try:
      response = await call_next(request)
      body = {"ts": start.isoformat(), "method": request.method, "path": request.url.path, "status": response.status_code}
      print(orjson.dumps(body).decode())
      return response
    except Exception as e:
      body = {"ts": start.isoformat(), "method": request.method, "path": request.url.path, "error": str(e)}
      print(orjson.dumps(body).decode())
      raise

# DB session dep

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/healthz")

def healthz():
    return {"ok": True}

@app.post("/api/login")

def login(payload: dict, db: Session = Depends(get_db)):
    email = (payload.get("email") or "").lower().strip()
    pw = payload.get("password") or ""
    user = db.scalar(select(models.User).where(models.User.email==email))
    if not user or not verify_password(pw, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid")
    csrf = uuid.uuid4().hex
    resp = JSONResponse({"ok": True, "csrf": csrf})
    set_session_cookie(resp, user.id, csrf)
    return resp

@app.get("/api/me")

def me(sess=Depends(require_session), db: Session = Depends(get_db)):
    return {"user_id": int(sess["uid"]) }

@app.get("/api/csrf")

def csrf(sess=Depends(require_session)):
    return {"csrf": sess.get("csrf")}

@app.post("/api/upload")

def upload_pdf(request: Request, f: UploadFile = File(...), db: Session = Depends(get_db)):
    # CSRF + auth
    _ = require_csrf(request)
    if f.content_type != "application/pdf":
        raise HTTPException(415, "pdf only")
    blob = f.file.read()
    if len(blob) > settings.PDF_MAX_MB * 1024 * 1024:
        raise HTTPException(413, "too large")
    fname = f.filename or f"upload-{uuid.uuid4().hex}.pdf"
    stmt = models.Statement(filename=fname, status="processing")
    db.add(stmt); db.commit(); db.refresh(stmt)
    # persist to uploads
    dest_dir = "/srv/finance/uploads"
    os.makedirs(dest_dir, exist_ok=True)
    path = os.path.join(dest_dir, f"{stmt.id}.pdf")
    with open(path, "wb") as wf:
        wf.write(blob)
    queue_parse.delay(stmt.id, path)
    return {"statement_id": stmt.id, "status": stmt.status}

@app.get("/api/statements")

def list_statements(db: Session = Depends(get_db)):
    rows = db.scalars(select(models.Statement).order_by(models.Statement.id.desc())).all()
    return [{"id": r.id, "filename": r.filename, "status": r.status, "error": r.error_message, "created_at": r.created_at} for r in rows]

@app.get("/api/transactions")

def list_transactions(export: str | None = None, db: Session = Depends(get_db)):
    q = select(models.Transaction).order_by(models.Transaction.id.desc())
    rows = db.scalars(q).all()
    data = [
        {
            "id": t.id,
            "statement_id": t.statement_id,
            "txn_date": t.txn_date.isoformat() if t.txn_date else None,
            "description": t.description,
            "amount": float(t.amount),
            "category": t.category.name if t.category else None,
        }
        for t in rows
    ]
    if export == "csv":
        sio = io.StringIO()
        w = csv.DictWriter(sio, fieldnames=list(data[0].keys()) if data else ["id"])
        w.writeheader(); w.writerows(data)
        return StreamingResponse(iter([sio.getvalue().encode()]), media_type="text/csv", headers={"Content-Disposition":"attachment; filename=transactions.csv"})
    if export == "xlsx":
        df = pd.DataFrame(data)
        bio = io.BytesIO(); df.to_excel(bio, index=False)
        return StreamingResponse(iter([bio.getvalue()]), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition":"attachment; filename=transactions.xlsx"})
    return data

@app.get("/api/rules")

def rules(db: Session = Depends(get_db)):
    rows = db.scalars(select(models.Rule).order_by(models.Rule.priority)).all()
    return [{"id": r.id, "pattern": r.pattern, "priority": r.priority, "category_id": r.category_id} for r in rows]

@app.post("/api/rules")

def add_rule(payload: dict, request: Request, db: Session = Depends(get_db)):
    _ = require_csrf(request)
    r = models.Rule(pattern=payload["pattern"], priority=int(payload.get("priority", 100)), category_id=payload.get("category_id"))
    db.add(r); db.commit(); db.refresh(r)
    return {"id": r.id}

@app.post("/api/rules/reapply")

def reapply_rules(request: Request, db: Session = Depends(get_db)):
    _ = require_csrf(request)
    from .repo import reapply_all
    reapply_all(db)
    return {"ok": True}
