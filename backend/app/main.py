from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.routes import router as auth_router
from app.config import settings
from app.db import init_db
from app.handles.routes import router as handles_router
from app.pin.routes import router as pin_router
from app.receive.routes import router as receive_router
from app.send.routes import router as send_router
from app.swap.routes import router as swap_router
from app.tee.routes import router as tee_router

app = FastAPI(title="Umbra API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(pin_router)
app.include_router(handles_router)
app.include_router(send_router)
app.include_router(receive_router)
app.include_router(swap_router)
app.include_router(tee_router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}
