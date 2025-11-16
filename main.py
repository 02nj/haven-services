from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
import yt_dlp
import os
import uuid
import requests

app = FastAPI(title="Haven Services API", version="1.0")

DOWNLOADS = "downloads"
IMAGES = "images"

os.makedirs(DOWNLOADS, exist_ok=True)
os.makedirs(IMAGES, exist_ok=True)


# -------------------------------
# YOUTUBE DOWNLOAD (MP3 + MP4)
# -------------------------------
@app.get("/youtube")
def youtube_download(url: str, format: str = "mp4"):
    try:
        file_id = str(uuid.uuid4())
        out = f"{DOWNLOADS}/{file_id}.%(ext)s"

        ydl_opts = {
            "outtmpl": out,
            "format": "bestaudio/best" if format == "mp3" else "bestvideo+bestaudio/best",
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}] if format == "mp3" else []
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            ext = "mp3" if format == "mp3" else info["ext"]

        filename = f"{file_id}.{ext}"
        return {"status": "success", "file": f"/download/{filename}"}

    except Exception as e:
        raise HTTPException(400, str(e))


@app.get("/download/{filename}")
def download_file(filename: str):
    path = f"{DOWNLOADS}/{filename}"
    if not os.path.exists(path):
        raise HTTPException(404, "File not found")
    return FileResponse(path, filename=filename)


# -------------------------------
# IMAGE HOSTING
# -------------------------------
@app.post("/image/upload")
async def upload_image(file: UploadFile = File(...)):
    file_id = f"{uuid.uuid4()}.png"
    file_path = os.path.join(IMAGES, file_id)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    return {"url": f"/image/{file_id}"}


@app.get("/image/{file_id}")
def get_image(file_id: str):
    path = os.path.join(IMAGES, file_id)
    if not os.path.exists(path):
        raise HTTPException(404, "Image not found")

    return FileResponse(path)


# -------------------------------
# REMOVE BACKGROUND
# (Using remove.bg API — FREE alternative optional)
# -------------------------------
@app.post("/image/remove-bg")
async def remove_bg(file: UploadFile = File(...)):
    try:
        api_key = os.getenv("REMOVE_BG_API", "")
        if not api_key:
            raise Exception("Missing REMOVE_BG_API")

        res = requests.post(
            "https://api.remove.bg/v1.0/removebg",
            files={"image_file": await file.read()},
            data={"size": "auto"},
            headers={"X-Api-Key": api_key},
        )

        if res.status_code != 200:
            raise Exception(res.text)

        output = f"{IMAGES}/{uuid.uuid4()}.png"
        with open(output, "wb") as f:
            f.write(res.content)

        return {"file": f"/image/{os.path.basename(output)}"}

    except Exception as e:
        raise HTTPException(400, str(e))
