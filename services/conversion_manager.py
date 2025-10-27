import threading
import subprocess
import uuid
from pathlib import Path
from typing import Dict, Any


class ConversionManager:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.video_dir = base_dir / "content" / "videos"
        self.audio_dir = base_dir / "content" / "audios"
        self.output_dir = base_dir / "content" / "converted"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Diccionario con tareas activas
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()

    def _convert(self, task_id: str, input_path: Path, output_path: Path):
        try:
            self._update_status(task_id, "procesando")

            cmd = ["ffmpeg", "-y", "-i", str(input_path), str(output_path)]
            subprocess.run(
                cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

            self._update_status(task_id, "listo")
            self.tasks[task_id]["output"] = str(output_path)

        except subprocess.CalledProcessError as e:
            self._update_status(task_id, "error", str(e))
        except Exception as e:
            self._update_status(task_id, "error", str(e))

    def _update_status(self, task_id: str, status: str, error: str = None):
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id]["estado"] = status
                if error:
                    self.tasks[task_id]["error"] = error

    def start_conversion(self, filename: str, formato: str, tipo: str) -> str:
        input_dir = self.video_dir if tipo == "video" else self.audio_dir
        input_path = input_dir / filename

        if not input_path.exists():
            raise FileNotFoundError(f"Archivo {filename} no encontrado en {input_dir}")

        output_name = f"{input_path.stem}_converted.{formato}"
        output_path = self.output_dir / output_name

        # Crear ID único para la tarea
        task_id = str(uuid.uuid4())
        task_data = {
            "id": task_id,
            "tipo": tipo,
            "archivo": filename,
            "formato": formato,
            "estado": "preparando",
            "output": None,
        }

        with self.lock:
            self.tasks[task_id] = task_data

        # Crear hilo para la conversión
        t = threading.Thread(
            target=self._convert, args=(task_id, input_path, output_path)
        )
        t.start()

        return task_id

    def get_task(self, task_id: str) -> Dict[str, Any]:
        with self.lock:
            return self.tasks.get(task_id, None)

    def list_tasks(self) -> Dict[str, Any]:
        with self.lock:
            return self.tasks.copy()
