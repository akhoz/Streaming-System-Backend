from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import videos, audios, conversion, upload, media_upload, dashboard

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
app.include_router(media_upload.router, prefix="/media", tags=["Media Upload"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])


@app.get("/")
def root():
    return {"message": "Backend operativo"}
