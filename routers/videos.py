from fastapi import APIRouter, HTTPException, Request, Path
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import List
import os
import mimetypes

router = APIRouter()

# 📂 Directorio de videos
VIDEO_DIR = os.path.join(os.path.dirname(__file__), "..", "content", "videos")


# ============================
# 📘 MODELOS PARA DOCUMENTACIÓN
# ============================


class VideoItem(BaseModel):
    nombre: str
    tipo: str
    tamaño_MB: float


class VideoListResponse(BaseModel):
    videos: List[VideoItem]


class ErrorResponse(BaseModel):
    detail: str


# ============================
# 🎞️ LISTAR VIDEOS DISPONIBLES
# ============================
@router.get(
    "/",
    response_model=VideoListResponse,
    responses={
        200: {"description": "Lista de videos disponibles"},
        404: {"model": ErrorResponse, "description": "Carpeta no encontrada"},
        500: {"model": ErrorResponse, "description": "Error interno"},
    },
    summary="Lista todos los videos disponibles",
    description="""
Devuelve una lista con los archivos de video disponibles en el servidor.  
Incluye el nombre, tipo MIME y tamaño (en MB) de cada archivo.
""",
)
def listar_videos():
    try:
        if not os.path.exists(VIDEO_DIR):
            raise HTTPException(
                status_code=404, detail="Carpeta de videos no encontrada"
            )

        files = []
        for f in os.listdir(VIDEO_DIR):
            if f.lower().endswith((".mp4", ".mkv", ".mov", ".avi")):
                file_path = os.path.join(VIDEO_DIR, f)
                media_type, _ = mimetypes.guess_type(file_path)
                size_mb = round(os.path.getsize(file_path) / (1024 * 1024), 2)
                files.append(
                    {
                        "nombre": f,
                        "tipo": media_type or "video/mp4",
                        "tamaño_MB": size_mb,
                    }
                )

        return {"videos": files}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================
# 🎬 STREAMING DE UN VIDEO
# ============================
@router.get(
    "/{filename}",
    responses={
        200: {"description": "Devuelve el video por streaming"},
        206: {"description": "Entrega parcial (streaming)"},
        404: {"model": ErrorResponse, "description": "Archivo no encontrado"},
        500: {"model": ErrorResponse, "description": "Error interno"},
    },
    summary="Reproduce un video específico por streaming",
    description="""
Devuelve el archivo de video en formato de transmisión (HTTP Range).  
Permite que el cliente reproduzca el video en tiempo real sin descargarlo completamente.
""",
)
def stream_video(
    filename: str = Path(
        ..., description="Nombre exacto del archivo de video (ej: pelicula.mp4)"
    ),
    request: Request = None,
):
    try:
        file_path = os.path.join(VIDEO_DIR, filename)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Archivo no encontrado")

        file_size = os.path.getsize(file_path)
        range_header = request.headers.get("range") if request else None
        media_type, _ = mimetypes.guess_type(file_path)
        media_type = media_type or "video/mp4"

        def iterfile(start=0, end=None):
            with open(file_path, "rb") as f:
                f.seek(start)
                remaining = end - start if end else file_size - start
                while remaining > 0:
                    chunk_size = 1024 * 1024  # 1MB
                    chunk = f.read(min(chunk_size, remaining))
                    if not chunk:
                        break
                    yield chunk
                    remaining -= len(chunk)

        if range_header:
            start, end = range_header.replace("bytes=", "").split("-")
            start = int(start)
            end = int(end) if end else file_size - 1
            headers = {
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
            }
            return StreamingResponse(
                iterfile(start, end + 1),
                status_code=206,
                headers=headers,
                media_type=media_type,
            )

        return StreamingResponse(iterfile(), media_type=media_type)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
