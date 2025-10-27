from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
import os

router = APIRouter()
CONTENT_DIR = os.path.join(os.path.dirname(__file__), "..", "content", "videos")


# 1️⃣ Listar videos disponibles
@router.get("/")
def listar_videos():
    try:
        files = [
            f
            for f in os.listdir(CONTENT_DIR)
            if f.lower().endswith((".mp4", ".mkv", ".mov", ".avi"))
        ]
        return JSONResponse({"videos": files})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 2️⃣ Stream de un video
@router.get("/{filename}")
def stream_video(filename: str, request: Request):
    file_path = os.path.join(CONTENT_DIR, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    file_size = os.path.getsize(file_path)
    range_header = request.headers.get("range")

    def iterfile(start=0, end=None):
        with open(file_path, "rb") as f:
            f.seek(start)
            remaining = end - start if end else file_size - start
            while remaining > 0:
                chunk_size = 1024 * 1024  # 1MB
                chunk = f.read(min(chunk_size, remaining))
                if not chunk:
                    break
                yield chunk
                remaining -= len(chunk)

    if range_header:
        start, end = range_header.replace("bytes=", "").split("-")
        start = int(start)
        end = int(end) if end else file_size - 1
        length = end - start + 1
        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
        }
        return StreamingResponse(
            iterfile(start, end + 1),
            status_code=206,
            headers=headers,
            media_type="video/mp4",
        )
    else:
        return StreamingResponse(iterfile(), media_type="video/mp4")
