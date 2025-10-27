from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
import subprocess
import os
from pathlib import Path

router = APIRouter()

# Directorios
BASE_DIR = Path(__file__).resolve().parent.parent
VIDEO_DIR = BASE_DIR / "content" / "videos"
AUDIO_DIR = BASE_DIR / "content" / "audios"
OUTPUT_DIR = BASE_DIR / "content" / "converted"

# Crear carpeta de salida si no existe
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# -------------------------------
# 🎬 Conversión de videos
# -------------------------------
@router.post("/video")
def convertir_video(
    filename: str = Query(..., description="Nombre del archivo de video existente"),
    formato: str = Query(..., description="Formato de salida (mp4 o mov)"),
):
    try:
        input_path = VIDEO_DIR / filename
        if not input_path.exists():
            raise HTTPException(
                status_code=404, detail="Archivo de video no encontrado"
            )

        if formato not in ["mp4", "mov"]:
            raise HTTPException(
                status_code=400,
                detail="Formato no soportado para video (usa mp4 o mov)",
            )

        output_name = f"{input_path.stem}_converted.{formato}"
        output_path = OUTPUT_DIR / output_name

        # Ejecutar ffmpeg
        cmd = [
            "ffmpeg",
            "-y",  # sobrescribir si existe
            "-i",
            str(input_path),
            str(output_path),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        return JSONResponse(
            {
                "mensaje": "Conversión de video completada ✅",
                "archivo_entrada": filename,
                "archivo_salida": output_name,
                "ruta_salida": str(output_path),
            }
        )

    except subprocess.CalledProcessError as e:
        raise HTTPException(
            status_code=500, detail=f"Error en FFmpeg: {e.stderr.decode('utf-8')}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------
# 🎵 Conversión de audios
# -------------------------------
@router.post("/audio")
def convertir_audio(
    filename: str = Query(..., description="Nombre del archivo de audio existente"),
    formato: str = Query(..., description="Formato de salida (mp3 o wav)"),
):
    try:
        input_path = AUDIO_DIR / filename
        if not input_path.exists():
            raise HTTPException(
                status_code=404, detail="Archivo de audio no encontrado"
            )

        if formato not in ["mp3", "wav"]:
            raise HTTPException(
                status_code=400,
                detail="Formato no soportado para audio (usa mp3 o wav)",
            )

        output_name = f"{input_path.stem}_converted.{formato}"
        output_path = OUTPUT_DIR / output_name

        cmd = ["ffmpeg", "-y", "-i", str(input_path), str(output_path)]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        return JSONResponse(
            {
                "mensaje": "Conversión de audio completada ✅",
                "archivo_entrada": filename,
                "archivo_salida": output_name,
                "ruta_salida": str(output_path),
            }
        )

    except subprocess.CalledProcessError as e:
        raise HTTPException(
            status_code=500, detail=f"Error en FFmpeg: {e.stderr.decode('utf-8')}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
