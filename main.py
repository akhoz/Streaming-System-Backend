from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import videos

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


@app.get("/")
def root():
    return {"message": "Backend operativo 🎬"}
