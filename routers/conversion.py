from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
from services.conversion_manager import ConversionManager

router = APIRouter()
BASE_DIR = Path(__file__).resolve().parent.parent
manager = ConversionManager(BASE_DIR)


# -------------------------------
# 🚀 Iniciar conversión
# -------------------------------
@router.post("/{tipo}")
def iniciar_conversion(
    tipo: str,
    filename: str = Query(..., description="Archivo existente"),
    formato: str = Query(..., description="Formato destino (mp3, mp4, mov)"),
):
    if tipo not in ["video", "audio"]:
        raise HTTPException(
            status_code=400, detail="Tipo inválido. Usa 'video' o 'audio'."
        )

    try:
        task_id = manager.start_conversion(filename, formato, tipo)
        return JSONResponse({"task_id": task_id, "estado": "preparando"})
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------
# 🔍 Ver estado de una tarea
# -------------------------------
@router.get("/status/{task_id}")
def obtener_estado(task_id: str):
    task = manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return JSONResponse(task)


# -------------------------------
# 📋 Listar todas las tareas
# -------------------------------
@router.get("/tasks")
def listar_tareas():
    return JSONResponse(manager.list_tasks())


# -------------------------------
# 💾 Descargar archivo convertido
# -------------------------------
@router.get("/download/{task_id}")
def descargar_resultado(task_id: str):
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
