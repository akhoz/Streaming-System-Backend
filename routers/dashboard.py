# routers/dashboard.py
from fastapi import APIRouter
from fastapi.responses import JSONResponse
import os
import psutil
import mimetypes
from datetime import datetime

router = APIRouter()

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
VIDEO_DIR = os.path.join(BASE_DIR, "content", "videos")
AUDIO_DIR = os.path.join(BASE_DIR, "content", "audios")

os.makedirs(VIDEO_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)


def scan_directory_stats(directory: str, valid_exts: tuple):
    """Escanea una carpeta y devuelve archivos + estadísticas básicas."""
    files = []
    total_size = 0
    count = 0

    if not os.path.exists(directory):
        return {"count": 0, "total_size_mb": 0, "files": []}

    for f in os.listdir(directory):
        if f.lower().endswith(valid_exts):
            path = os.path.join(directory, f)
            size = os.path.getsize(path)
            total_size += size
            count += 1
            files.append(
                {
                    "nombre": f,
                    "tipo": mimetypes.guess_type(path)[0] or "desconocido",
                    "tamaño_MB": round(size / (1024 * 1024), 2),
                    "ultima_modificacion": datetime.fromtimestamp(
                        os.path.getmtime(path)
                    ).isoformat(),
                }
            )

    return {
        "count": count,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "files": sorted(files, key=lambda x: x["ultima_modificacion"], reverse=True)[
            :5
        ],  # top 5 recientes
    }


@router.get(
    "/metrics",
    summary="📊 Muestra estadísticas en tiempo real del sistema y archivos",
    description="Devuelve información sobre almacenamiento, rendimiento y contenido multimedia del servidor.",
)
def get_dashboard_metrics():
    # Estadísticas del sistema
    cpu_percent = psutil.cpu_percent(interval=0.5)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    # Escanear carpetas de videos y audios
    video_stats = scan_directory_stats(VIDEO_DIR, (".mp4", ".mov", ".mkv", ".avi"))
    audio_stats = scan_directory_stats(
        AUDIO_DIR, (".mp3", ".wav", ".flac", ".ogg", ".m4a")
    )

    response = {
        "sistema": {
            "cpu_uso_porcentaje": cpu_percent,
            "memoria_uso_porcentaje": memory.percent,
            "almacenamiento": {
                "usado_GB": round(disk.used / (1024**3), 2),
                "total_GB": round(disk.total / (1024**3), 2),
                "porcentaje": disk.percent,
            },
        },
        "contenido": {
            "videos": video_stats,
            "audios": audio_stats,
            "total_archivos": video_stats["count"] + audio_stats["count"],
            "peso_total_MB": round(
                video_stats["total_size_mb"] + audio_stats["total_size_mb"], 2
            ),
        },
        "timestamp": datetime.now().isoformat(),
    }

    return JSONResponse(content=response)
