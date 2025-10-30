import json
from pathlib import Path
from threading import Lock


class FileRegistry:
    """
    Registro simple en JSON que almacena el propietario de cada archivo subido.
    Estructura:
    {
        "intro.mp4": {"owner": "advillalobos"},
        "theme.mp3": {"owner": "izack"}
    }
    """

    def __init__(self, base_dir: Path):
        self.file = base_dir / "content" / "file_metadata.json"
        self.lock = Lock()
        self.file.parent.mkdir(parents=True, exist_ok=True)
        if not self.file.exists():
            self.file.write_text("{}", encoding="utf-8")

    def _read(self):
        try:
            with self.file.open("r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}

    def _write(self, data):
        with self.file.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def register(self, filename: str, owner: str):
        """Registra o actualiza el propietario de un archivo."""
        with self.lock:
            data = self._read()
            data[filename] = {"owner": owner}
            self._write(data)

    def get_owner(self, filename: str) -> str:
        """Devuelve el propietario de un archivo o 'unknown' si no está registrado."""
        data = self._read()
        return data.get(filename, {}).get("owner", "unknown")

    def all(self):
        """Devuelve todos los registros."""
        return self._read()
