from fastapi import APIRouter, HTTPException, Request, Path
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from pydantic import BaseModel
from typing import List
import aiofiles
import mimetypes
import os

router = APIRouter()

# 📂 Directorio base de videos
VIDEO_DIR = os.path.join(os.path.dirname(__file__), "..", "content", "videos")
CHUNK_SIZE = 1024 * 1024 * 8  # 8MB por bloque


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
    description="Devuelve los videos almacenados en el servidor, con nombre, tipo MIME y tamaño (MB).",
)
async def listar_videos():
    try:
        if not os.path.exists(VIDEO_DIR):
            raise HTTPException(
                status_code=404, detail="Carpeta de videos no encontrada"
            )

        files = []
        for f in os.listdir(VIDEO_DIR):
            if f.lower().endswith((".mp4", ".mkv", ".mov", ".avi")):
                path = os.path.join(VIDEO_DIR, f)
                tipo, _ = mimetypes.guess_type(path)
                size_mb = round(os.path.getsize(path) / (1024 * 1024), 2)
                files.append(
                    {
                        "nombre": f,
                        "tipo": tipo or "video/mp4",
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
    description="Permite reproducir un video directamente en el navegador con soporte de carga progresiva.",
)
async def stream_video(
    filename: str = Path(..., description="Nombre del video"),
    request: Request = None,
):
    file_path = os.path.join(VIDEO_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    file_size = os.path.getsize(file_path)
    media_type, _ = mimetypes.guess_type(file_path)
    media_type = media_type or "video/mp4"
    range_header = request.headers.get("range")

    # 🧠 Función generadora de chunks (asíncrona)
    async def iterfile(start=0, end=None):
        async with aiofiles.open(file_path, "rb") as f:
            await f.seek(start)
            remaining = (end - start) if end else (file_size - start)
            while remaining > 0:
                chunk = await f.read(min(CHUNK_SIZE, remaining))
                if not chunk:
                    break
                yield chunk
                remaining -= len(chunk)

    # 🔍 Soporte para Range Requests (carga progresiva)
    if range_header:
        try:
            range_header = range_header.strip().lower().replace("bytes=", "")
            start_str, end_str = range_header.split("-")
            start = int(start_str)
            end = int(end_str) if end_str else file_size - 1
        except ValueError:
            raise HTTPException(status_code=400, detail="Encabezado Range inválido")

        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Cache-Control": "public, max-age=3600",
            "Transfer-Encoding": "chunked",
        }

        return StreamingResponse(
            iterfile(start, end + 1),
            status_code=206,
            headers=headers,
            media_type=media_type,
        )

    # 📦 Respuesta completa (sin Range)
    headers = {"Cache-Control": "public, max-age=3600"}
    return StreamingResponse(iterfile(), media_type=media_type, headers=headers)


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
    description="Permite descargar el archivo de video original completo.",
)
async def descargar_video(
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
