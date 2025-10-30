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
CHUNK_SIZE = 1024 * 256  # 256KB - Óptimo para streaming progresivo


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
# 🎬 STREAMING DE UN VIDEO (OPTIMIZADO)
# ============================
@router.get(
    "/{filename}",
    responses={
        200: {"description": "Streaming de video"},
        206: {"description": "Contenido parcial (streaming progresivo)"},
        404: {"model": ErrorResponse},
    },
    summary="Reproduce un video específico por streaming",
    description="Permite reproducir un video directamente en el navegador con soporte de carga progresiva optimizada.",
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

    # 🧠 Función generadora de chunks (asíncrona y optimizada)
    async def iterfile(start=0, end=None):
        async with aiofiles.open(file_path, "rb") as f:
            await f.seek(start)
            remaining = (end - start + 1) if end else (file_size - start)

            while remaining > 0:
                chunk_size = min(CHUNK_SIZE, remaining)
                chunk = await f.read(chunk_size)

                if not chunk:
                    break

                yield chunk
                remaining -= len(chunk)

    # 🔍 Soporte para Range Requests (carga progresiva)
    if range_header:
        try:
            # Parsear el header Range
            range_header = range_header.strip().lower()
            if not range_header.startswith("bytes="):
                raise HTTPException(status_code=400, detail="Formato de Range inválido")

            range_value = range_header.replace("bytes=", "")

            # Manejar múltiples rangos (tomar solo el primero)
            if "," in range_value:
                range_value = range_value.split(",")[0]

            start_str, end_str = range_value.split("-")

            # Calcular start y end
            start = int(start_str) if start_str else 0
            end = int(end_str) if end_str else file_size - 1

            # Validar rangos
            if start < 0 or start >= file_size:
                raise HTTPException(
                    status_code=416, detail="Rango solicitado fuera de límites"
                )

            # Asegurar que end no exceda el tamaño del archivo
            end = min(end, file_size - 1)

            # Calcular el tamaño del contenido a enviar
            content_length = end - start + 1

        except (ValueError, IndexError):
            raise HTTPException(status_code=400, detail="Encabezado Range mal formado")

        # Headers optimizados para streaming parcial
        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(content_length),
            "Cache-Control": "public, max-age=3600",
            "Connection": "keep-alive",
        }

        return StreamingResponse(
            iterfile(start, end),
            status_code=206,
            headers=headers,
            media_type=media_type,
        )

    # 📦 Respuesta completa (sin Range) - Primera solicitud
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(file_size),
        "Cache-Control": "public, max-age=3600",
    }

    return StreamingResponse(
        iterfile(), media_type=media_type, headers=headers, status_code=200
    )


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
