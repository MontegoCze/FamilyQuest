from fastapi import FastAPI, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError

from app.api.v1.router import api_router
from app.config import settings
from app.core.security import decode_access_token
from app.database import SessionLocal, init_db
from app.models import FamilyMember, User
from app.realtime import realtime_manager

init_db()

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.middleware("http")
async def broadcast_mutations(request: Request, call_next):
    response = await call_next(request)
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and response.status_code < 400:
        family_id = None
        authorization = request.headers.get("authorization", "")
        if authorization.lower().startswith("bearer "):
            db = SessionLocal()
            try:
                payload = decode_access_token(authorization[7:])
                email = payload.get("sub")
                member = db.query(FamilyMember.family_id).join(User).filter(
                    User.email == email, User.is_active.is_(True)
                ).first()
                family_id = str(member[0]) if member else None
            except (JWTError, TypeError):
                family_id = None
            finally:
                db.close()
        if family_id:
            await realtime_manager.broadcast({"type": "data_changed", "resource": request.url.path}, family_id)
    return response


@app.websocket("/api/v1/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(default="")) -> None:
    try:
        payload = decode_access_token(token)
    except (JWTError, TypeError):
        await websocket.close(code=1008)
        return
    email = payload.get("sub")
    db = SessionLocal()
    try:
        member = db.query(FamilyMember.family_id).join(User).filter(
            User.email == email, User.is_active.is_(True)
        ).first()
    finally:
        db.close()
    family_id = str(member[0]) if member else None
    if not family_id:
        await websocket.close(code=1008)
        return
    await realtime_manager.connect(websocket, family_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await realtime_manager.disconnect(websocket, family_id)


@app.on_event("startup")
def startup_event() -> None:
    init_db()


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}
