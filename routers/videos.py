from fastapi import APIRouter, HTTPException, Request, Path
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
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
    summary="Lista todos los videos disponibles",
    description="Devuelve todos los videos almacenados en el servidor, con nombre, tipo MIME y tamaño (MB).",
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

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================
# 🎬 STREAMING DE UN VIDEO
# ============================
@router.get(
    "/{filename}",
    responses={
        200: {"description": "Streaming de video"},
        404: {"model": ErrorResponse},
    },
    summary="Reproduce un video específico por streaming",
    description="Permite ver un video directamente desde el navegador sin descargarlo completamente.",
)
def stream_video(
    filename: str = Path(..., description="Nombre del video"), request: Request = None
):
    file_path = os.path.join(VIDEO_DIR, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    file_size = os.path.getsize(file_path)
    range_header = request.headers.get("range")
    media_type, _ = mimetypes.guess_type(file_path)
    media_type = media_type or "video/mp4"

    def iterfile(start=0, end=None):
        with open(file_path, "rb") as f:
            f.seek(start)
            remaining = end - start if end else file_size - start
            while remaining > 0:
                chunk_size = 1024 * 1024
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


# ============================
# 💾 DESCARGAR VIDEO DIRECTAMENTE
# ============================
@router.get(
    "/download/{filename}",
    responses={
        200: {"description": "Devuelve el archivo de video para descarga"},
        404: {"model": ErrorResponse, "description": "Archivo no encontrado"},
    },
    summary="Descarga un video directamente",
    description="Devuelve el archivo solicitado en formato descargable (Content-Disposition: attachment).",
)
def descargar_video(
    filename: str = Path(..., description="Nombre del video a descargar"),
):
    file_path = os.path.join(VIDEO_DIR, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    media_type, _ = mimetypes.guess_type(file_path)
    media_type = media_type or "video/mp4"

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
