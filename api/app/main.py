from __future__ import annotations
import os, io, uuid, orjson
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Request, Path
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
@app.post("/api/auth/login")
def login(payload: dict, db: Session = Depends(get_db)):
    """
    Authenticate a user by email and password.  Returns a JSON object with
    ``csrf`` which must be included as an ``x-csrf-token`` header in
    subsequent POST/PUT/DELETE requests.  On success a signed session
    cookie is set in the response.
    """
    email = (payload.get("email") or "").lower().strip()
    pw = payload.get("password") or ""
    user = db.scalar(select(models.User).where(models.User.email == email))
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

@app.post("/api/statements")
@app.post("/api/upload")
def upload_pdf(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Upload a PDF bank statement.  The file must have content type
    ``application/pdf`` and must not exceed ``PDF_MAX_MB``.  On success a
    ``Statement`` row is created with status ``processing`` and the file is
    persisted to the uploads directory.  A background Celery task parses
    the PDF asynchronously; once complete the statement status is updated
    to ``processed`` or ``failed``.  Returns the new statement ID and
    current status.
    """
    _ = require_csrf(request)
    if file.content_type != "application/pdf":
        raise HTTPException(415, "pdf only")
    blob = file.file.read()
    if len(blob) > settings.PDF_MAX_MB * 1024 * 1024:
        raise HTTPException(413, "too large")
    fname = file.filename or f"upload-{uuid.uuid4().hex}.pdf"
    stmt = models.Statement(filename=fname, status="processing")
    db.add(stmt); db.commit(); db.refresh(stmt)
    # persist to uploads
    dest_dir = "/srv/finance/uploads"
    os.makedirs(dest_dir, exist_ok=True)
    path = os.path.join(dest_dir, f"{stmt.id}.pdf")
    with open(path, "wb") as wf:
        wf.write(blob)
    # queue parse via celery
    queue_parse.delay(stmt.id, path)
    return {"statement_id": stmt.id, "status": stmt.status}

@app.get("/api/statements")
def list_statements(db: Session = Depends(get_db)):
    """
    List all uploaded statements.  Each statement includes its filename,
    upload timestamp, current status and the number of transactions parsed.
    """
    rows = db.scalars(select(models.Statement).order_by(models.Statement.created_at.desc())).all()
    out = []
    for r in rows:
        tx_count = db.scalar(select(func.count(models.Transaction.id)).where(models.Transaction.statement_id == r.id))
        out.append({
            "id": r.id,
            "filename": r.filename,
            "status": r.status,
            "error": r.error_message,
            "created_at": r.created_at,
            "transactions_count": tx_count,
        })
    return out

@app.get("/api/transactions")
def list_transactions(statement_id: int | None = None, export: str | None = None, db: Session = Depends(get_db)):
    """
    List transactions.  If ``statement_id`` is provided the results are
    filtered to that statement.  The response includes posting_date,
    transaction_date, description, amount, category and subcategory.  The
    ``export`` parameter can be ``csv`` or ``xlsx`` to download the
    results in tabular form.
    """
    q = select(models.Transaction)
    if statement_id is not None:
        q = q.where(models.Transaction.statement_id == statement_id)
    q = q.order_by(models.Transaction.id.desc())
    rows = db.scalars(q).all()
    data = []
    for t in rows:
        data.append({
            "id": t.id,
            "statement_id": t.statement_id,
            "posting_date": t.post_date.isoformat() if t.post_date else None,
            "transaction_date": t.txn_date.isoformat() if t.txn_date else None,
            "description": t.description,
            "amount": float(t.amount),
            "category": t.category.name if t.category else None,
            "subcategory": t.subcategory,
        })
    # handle exports
    if export == "csv":
        # Flatten into CSV
        sio = io.StringIO()
        fieldnames = list(data[0].keys()) if data else ["id"]
        w = csv.DictWriter(sio, fieldnames=fieldnames)
        w.writeheader(); w.writerows(data)
        return StreamingResponse(
            iter([sio.getvalue().encode()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=transactions.csv"},
        )
    if export == "xlsx":
        df = pd.DataFrame(data)
        bio = io.BytesIO(); df.to_excel(bio, index=False)
        return StreamingResponse(
            iter([bio.getvalue()]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=transactions.xlsx"},
        )
    return data

@app.get("/api/categories")
def list_categories(db: Session = Depends(get_db)):
    """Return all available categories ordered alphabetically."""
    rows = db.scalars(select(models.Category).order_by(models.Category.name)).all()
    return [{"id": c.id, "name": c.name} for c in rows]


@app.get("/api/rules")
def list_rules(db: Session = Depends(get_db)):
    """
    Return all active rules in order of priority and creation.  Each rule
    includes the pattern (keyword), category name, subcategory, status and
    created timestamp.
    """
    rows = db.scalars(select(models.Rule).order_by(models.Rule.priority, models.Rule.created_at)).all()
    out = []
    for r in rows:
        out.append({
            "id": r.id,
            "keyword": r.pattern,
            "priority": r.priority,
            "category": r.category.name if r.category else None,
            "subcategory": r.subcategory,
            "status": r.status,
            "created_at": r.created_at,
        })
    return out

@app.post("/api/rules")
def add_rule(payload: dict, request: Request, db: Session = Depends(get_db)):
    """
    Create a new keyword rule.  The payload should include ``keyword``
    (case‑insensitive substring to match), ``category`` (the name of the
    category to assign) and an optional ``subcategory``.  If the category
    does not exist it will be created.  Returns the new rule ID.
    """
    _ = require_csrf(request)
    keyword = (payload.get("keyword") or payload.get("pattern") or "").strip()
    if not keyword:
        raise HTTPException(400, "keyword required")
    category_name = (payload.get("category") or "").strip() or None
    subcat = (payload.get("subcategory") or "").strip() or None
    priority = int(payload.get("priority", 100))
    # resolve category
    category_id = None
    if category_name:
        cat = db.scalar(select(models.Category).where(models.Category.name == category_name))
        if not cat:
            cat = models.Category(name=category_name)
            db.add(cat)
            db.commit(); db.refresh(cat)
        category_id = cat.id
    r = models.Rule(pattern=keyword, priority=priority, category_id=category_id, subcategory=subcat, status="active")
    db.add(r); db.commit(); db.refresh(r)
    return {"id": r.id}


@app.delete("/api/rules/{rule_id}")
def delete_rule(rule_id: int = Path(..., gt=0), request: Request = None, db: Session = Depends(get_db)):
    """
    Delete a rule by its identifier.  Only authenticated sessions with a
    valid CSRF token may remove rules.  If the rule does not exist a
    404 is returned.
    """
    if request is not None:
        _ = require_csrf(request)
    r = db.get(models.Rule, rule_id)
    if not r:
        raise HTTPException(404, "not found")
    db.delete(r); db.commit()
    return {"ok": True}

@app.post("/api/reprocess")
@app.post("/api/rules/reapply")
def reapply_rules(request: Request, db: Session = Depends(get_db)):
    """
    Reapply the current set of rules to all existing transactions.  This
    endpoint can be used after adding or modifying rules to update the
    categorisation of historical data.  Requires a CSRF token.
    """
    _ = require_csrf(request)
    from .repo import reapply_all
    reapply_all(db)
    return {"ok": True}
