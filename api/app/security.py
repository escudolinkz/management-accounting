from passlib.hash import bcrypt
from itsdangerous import TimestampSigner, BadSignature
from fastapi import Request, HTTPException
from fastapi.responses import Response
from app.config import settings

signer = TimestampSigner(settings.NEXTAUTH_SECRET)

def hash_password(pw: str) -> str:
    return bcrypt.hash(pw)

def verify_password(pw: str, hashed: str) -> bool:
    return bcrypt.verify(pw, hashed)

def set_session_cookie(resp: Response, user_id: int, csrf_token: str):
    payload = f"uid={user_id};csrf={csrf_token}"
    signed = signer.sign(payload.encode()).decode()
    resp.set_cookie(
        key="ma_session",
        value=signed,
        httponly=True,
        samesite="Lax",
        secure=False,
        path="/",
    )

def require_session(request: Request) -> dict:
    raw = request.cookies.get("ma_session")
    if not raw:
        raise HTTPException(status_code=401, detail="unauthorized")
    try:
        data = signer.unsign(raw, max_age=60*60*8).decode()
        parts = dict(kv.split("=") for kv in data.split(";"))
        return parts
    except BadSignature:
        raise HTTPException(status_code=401, detail="bad session")

def require_csrf(request: Request):
    sess = require_session(request)
    hdr = request.headers.get("x-csrf-token")
    if not hdr or hdr != sess.get("csrf"):
        raise HTTPException(status_code=403, detail="csrf")
    return sess
