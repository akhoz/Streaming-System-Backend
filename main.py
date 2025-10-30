from fastapi.middleware.cors import CORSMiddleware
from routers import videos, audios, conversion, upload
from fastapi import FastAPI, Depends, HTTPException, status
from sqlmodel import select, Session
from services.storage.db import init_db, get_session
from services.storage.model import User
from services.storage.model import LoginIn

app = FastAPI(title="Distributed Multimedia Platform")

# Permitir acceso desde tu frontend o localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # luego puedes restringirlo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(videos.router, prefix="/videos", tags=["Videos"])
app.include_router(audios.router, prefix="/audios", tags=["Audios"])
app.include_router(conversion.router, prefix="/convert", tags=["Conversiones"])
app.include_router(upload.router, prefix="/convert", tags=["Conversión por Upload"])


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
def root():
    return {"message": "Backend operativo"}


@app.post("/users", status_code=201)
def create_user(email: str, password: str, db: Session = Depends(get_session)):
    # simple: validación básica de duplicados
    exists = db.exec(select(User).where(User.email == email)).first()
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email ya registrado"
        )
    user = User(email=email, password=password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "email": user.email}


@app.get("/users")
def list_users(db: Session = Depends(get_session)):
    return db.exec(select(User)).all()


@app.post("/auth/login")
def login(data: LoginIn, db: Session = Depends(get_session)):
    user = db.exec(select(User).where(User.email == data.email)).first()
    if not user or user.password != data.password:
        # más seguro no revelar cuál de los dos falló
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas"
        )
    return {"ok": True}
