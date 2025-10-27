from fastapi import APIRouter, HTTPException, Query, Path
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path as FilePath
from pydantic import BaseModel
from typing import Optional, Dict, Any
from services.conversion_manager import ConversionManager

router = APIRouter()
BASE_DIR = FilePath(__file__).resolve().parent.parent
manager = ConversionManager(BASE_DIR)

# =========================
# 🧱 MODELOS PARA SWAGGER
# =========================


class ConversionStartResponse(BaseModel):
    task_id: str
    estado: str = "preparando"
    descripcion: str = "Conversión iniciada correctamente"


class ConversionStatusResponse(BaseModel):
    id: str
    tipo: str
    archivo: str
    formato: str
    estado: str
    output: Optional[str] = None
    error: Optional[str] = None


class ErrorResponse(BaseModel):
    detail: str


# =========================================
# 🚀 Iniciar conversión (POST /convert/{tipo})
# =========================================
@router.post(
    "/{tipo}",
    response_model=ConversionStartResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Parámetros inválidos"},
        404: {"model": ErrorResponse, "description": "Archivo no encontrado"},
        500: {"model": ErrorResponse, "description": "Error interno"},
    },
    summary="Inicia la conversión de un archivo",
    description="""
Crea una nueva tarea de conversión (audio o video).  
Devuelve un **task_id** que puedes usar para consultar el estado o descargar el archivo convertido.
""",
)
def iniciar_conversion(
    tipo: str = Path(..., description="Tipo de archivo: 'video' o 'audio'"),
    filename: str = Query(..., description="Nombre del archivo existente"),
    formato: str = Query(..., description="Formato destino (mp3, mp4, mov)"),
):
    if tipo not in ["video", "audio"]:
        raise HTTPException(
            status_code=400, detail="Tipo inválido. Usa 'video' o 'audio'."
        )

    try:
        task_id = manager.start_conversion(filename, formato, tipo)
        return ConversionStartResponse(task_id=task_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================================
# 🔍 Ver estado de una tarea
# =========================================
@router.get(
    "/status/{task_id}",
    response_model=ConversionStatusResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Tarea no encontrada"},
    },
    summary="Consulta el estado de una conversión",
    description="Devuelve información sobre una tarea específica (estado, archivo, formato, etc.).",
)
def obtener_estado(
    task_id: str = Path(..., description="ID único de la tarea de conversión"),
):
    task = manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return task


# =========================================
# 📋 Listar todas las tareas
# =========================================
@router.get(
    "/tasks",
    response_model=Dict[str, Any],
    summary="Lista todas las tareas de conversión activas o completadas",
    description="Muestra todas las tareas registradas en el ConversionManager, con su estado actual.",
)
def listar_tareas():
    return manager.list_tasks()


# =========================================
# 💾 Descargar archivo convertido
# =========================================
@router.get(
    "/download/{task_id}",
    responses={
        200: {"description": "Devuelve el archivo convertido"},
        400: {
            "model": ErrorResponse,
            "description": "La conversión aún no ha finalizado",
        },
        404: {"model": ErrorResponse, "description": "Tarea o archivo no encontrado"},
    },
    summary="Descarga el archivo convertido",
    description="Descarga directamente el archivo generado una vez que la conversión ha finalizado.",
)
def descargar_resultado(
    task_id: str = Path(..., description="ID único de la tarea de conversión"),
):
    task = manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    if task["estado"] != "listo":
        raise HTTPException(status_code=400, detail="La tarea aún no ha finalizado")

    output_path = Path(task["output"])
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Archivo convertido no encontrado")

    return FileResponse(
        path=output_path,
        filename=output_path.name,
        media_type="application/octet-stream",
    )
