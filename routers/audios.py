from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
import os, mimetypes

router = APIRouter()
CONTENT_DIR = os.path.join(os.path.dirname(__file__), "..", "content", "audios")


# 1️⃣ Listar audios disponibles
@router.get("/")
def listar_audios():
    try:
        files = [
            f
            for f in os.listdir(AUDIO_DIR)
            if f.lower().endswith((".mp3", ".wav", ".flac", ".ogg", ".m4a"))
        ]
        return JSONResponse({"audios": files})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 2️⃣ Stream de audio
@router.get("/{filename}")
def stream_audio(filename: str, request: Request):
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
                chunk_size = 1024 * 512  # 512 KB por chunk
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
    else:
        return StreamingResponse(iterfile(), media_type=media_type)
