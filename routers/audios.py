from fastapi import APIRouter, HTTPException, Request, Path
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from pydantic import BaseModel
from typing import List
import os
import mimetypes

router = APIRouter()
AUDIO_DIR = os.path.join(os.path.dirname(__file__), "..", "content", "audios")


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
        404: {"model": ErrorResponse},
    },
    summary="Reproduce un audio específico por streaming",
    description="Permite escuchar un audio directamente desde el navegador sin descargarlo completamente.",
)
def stream_audio(
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
            remaining = end - start if end else file_size - start
            while remaining > 0:
                chunk_size = 1024 * 512
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


@router.get(
    "/download/{filename}",
    responses={
        200: {"description": "Devuelve el archivo de audio para descarga"},
        404: {"model": ErrorResponse, "description": "Archivo no encontrado"},
    },
    summary="Descarga un audio directamente",
    description="Permite descargar un archivo de audio desde el servidor.",
)
def descargar_audio(
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
