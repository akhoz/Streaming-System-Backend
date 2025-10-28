from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
import subprocess
import shutil
import uuid

router = APIRouter()
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "content" / "uploads"
OUTPUT_DIR = BASE_DIR / "content" / "converted"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@router.post(
    "/upload/video",
    summary="Sube y convierte un video directamente",
    description="""
Permite subir un archivo de video y convertirlo inmediatamente a otro formato (por ejemplo .mp4 → .mov).
Devuelve el archivo convertido para descarga directa.
""",
)
async def convertir_video_subido(
    file: UploadFile = File(
        ..., description="Archivo de video a convertir (.mp4, .mov, etc.)"
    ),
    formato: str = Form(..., description="Formato de salida (mp4 o mov)"),
):
    try:
        # Verificar formato
        if formato not in ["mp4", "mov"]:
            raise HTTPException(
                status_code=400, detail="Formato de salida no soportado (usa mp4 o mov)"
            )

        # Guardar archivo temporalmente
        temp_name = f"{uuid.uuid4()}_{file.filename}"
        input_path = UPLOAD_DIR / temp_name

        with input_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Crear nombre de salida
        output_name = f"{input_path.stem}_converted.{formato}"
        output_path = OUTPUT_DIR / output_name

        # Ejecutar FFmpeg
        cmd = ["ffmpeg", "-y", "-i", str(input_path), str(output_path)]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Eliminar el archivo temporal
        input_path.unlink(missing_ok=True)

        # Devolver el archivo convertido directamente
        return FileResponse(
            path=output_path,
            filename=output_name,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={output_name}"},
        )

    except subprocess.CalledProcessError as e:
        raise HTTPException(
            status_code=500, detail=f"Error en FFmpeg: {e.stderr.decode('utf-8')}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
