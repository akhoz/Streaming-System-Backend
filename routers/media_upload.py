from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path
import shutil
import mimetypes
from services.file_registry import FileRegistry

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent
CONTENT_DIR = BASE_DIR / "content"
VIDEO_DIR = CONTENT_DIR / "videos"
AUDIO_DIR = CONTENT_DIR / "audios"

VIDEO_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

registry = FileRegistry(BASE_DIR)


@router.post(
    "/upload",
    summary="Sube un archivo de audio o video",
    description="Sube un archivo multimedia (audio o video) y lo almacena automáticamente en la carpeta correspondiente.",
)
async def upload_media(
    file: UploadFile = File(..., description="Archivo de audio o video"),
    owner: str = Form(
        "unknown", description="Propietario o usuario que sube el archivo"
    ),
):
    try:
        # Detectar tipo MIME
        mime_type, _ = mimetypes.guess_type(file.filename)
        mime_type = mime_type or ""

        # Verificar si es audio o video
        if mime_type.startswith("video/"):
            folder = VIDEO_DIR
            tipo = "video"
        elif mime_type.startswith("audio/"):
            folder = AUDIO_DIR
            tipo = "audio"
        else:
            # Si no se puede detectar por MIME, usamos la extensión
            ext = file.filename.lower().split(".")[-1]
            if ext in ["mp4", "mov", "avi", "mkv"]:
                folder = VIDEO_DIR
                tipo = "video"
            elif ext in ["mp3", "wav", "flac", "m4a", "ogg"]:
                folder = AUDIO_DIR
                tipo = "audio"
            else:
                raise HTTPException(
                    status_code=400, detail="Formato de archivo no soportado"
                )

        # Ruta final
        dest_path = folder / file.filename

        # Guardar archivo en disco
        with dest_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Registrar en metadatos (opcional)
        registry.register(file.filename, owner)

        return JSONResponse(
            {
                "mensaje": "Archivo subido correctamente ✅",
                "archivo": file.filename,
                "tipo": tipo,
                "propietario": owner,
                "ruta": str(dest_path),
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al subir archivo: {e}")
