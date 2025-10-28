from fastapi import APIRouter, HTTPException, Request, Path
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from pydantic import BaseModel
from typing import List
import os
import mimetypes

router = APIRouter()
AUDIO_DIR = os.path.join(os.path.dirname(__file__), "..", "content", "audios")
CHUNK_SIZE = 1024 * 256  # 256KB - Óptimo para streaming


class AudioItem(BaseModel):
    nombre: str
    tipo: str
    tamaño_MB: float


class AudioListResponse(BaseModel):
    audios: List[AudioItem]


class ErrorResponse(BaseModel):
    detail: str


@router.get(
    "/",
    response_model=AudioListResponse,
    summary="Lista todos los audios disponibles",
    description="Devuelve todos los audios disponibles en el servidor con nombre, tipo MIME y tamaño (MB).",
)
def listar_audios():
    try:
        if not os.path.exists(AUDIO_DIR):
            raise HTTPException(
                status_code=404, detail="Carpeta de audios no encontrada"
            )

        files = []
        for f in os.listdir(AUDIO_DIR):
            if f.lower().endswith((".mp3", ".wav", ".flac", ".ogg", ".m4a")):
                file_path = os.path.join(AUDIO_DIR, f)
                media_type, _ = mimetypes.guess_type(file_path)
                size_mb = round(os.path.getsize(file_path) / (1024 * 1024), 2)
                files.append(
                    {
                        "nombre": f,
                        "tipo": media_type or "audio/mpeg",
                        "tamaño_MB": size_mb,
                    }
                )

        return {"audios": files}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{filename}",
    responses={
        200: {"description": "Streaming de audio"},
        206: {"description": "Contenido parcial (streaming progresivo)"},
        404: {"model": ErrorResponse},
    },
    summary="Reproduce un audio específico por streaming",
    description="Permite escuchar un audio directamente desde el navegador sin descargarlo completamente.",
)
async def stream_audio(
    filename: str = Path(..., description="Nombre del audio"), request: Request = None
):
    file_path = os.path.join(AUDIO_DIR, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    file_size = os.path.getsize(file_path)
    range_header = request.headers.get("range")
    media_type, _ = mimetypes.guess_type(file_path)
    media_type = media_type or "audio/mpeg"

    def iterfile(start=0, end=None):
        with open(file_path, "rb") as f:
            f.seek(start)
            remaining = (end - start + 1) if end else (file_size - start)

            while remaining > 0:
                chunk_size = min(CHUNK_SIZE, remaining)
                chunk = f.read(chunk_size)

                if not chunk:
                    break

                yield chunk
                remaining -= len(chunk)

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

    # Respuesta completa sin Range
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(file_size),
        "Cache-Control": "public, max-age=3600",
    }

    return StreamingResponse(
        iterfile(), media_type=media_type, headers=headers, status_code=200
    )


@router.get(
    "/download/{filename}",
    responses={
        200: {"description": "Devuelve el archivo de audio para descarga"},
        404: {"model": ErrorResponse, "description": "Archivo no encontrado"},
    },
    summary="Descarga un audio directamente",
    description="Permite descargar un archivo de audio desde el servidor.",
)
async def descargar_audio(
    filename: str = Path(..., description="Nombre del audio a descargar"),
):
    file_path = os.path.join(AUDIO_DIR, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    media_type, _ = mimetypes.guess_type(file_path)
    media_type = media_type or "audio/mpeg"

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
