import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List

import requests
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

app = FastAPI(title="Applogize Hume Bridge")

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

HUME_API_BASE = "https://api.hume.ai/v0"
HUME_JOB_TIMEOUT_SECONDS = 60
HUME_POLL_INTERVAL_SECONDS = 1

WAV_MIME_TYPES = {
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/vnd.wave",
}

TARGET_EMOTION_KEYS = [
    "calmness",
    "relief",
    "contentment",
    "love",
    "sympathy",
    "romance",
    "anger",
    "contempt",
    "disgust",
    "distress",
    "sadness",
    "disappointment",
    "guilt",
    "shame",
    "interest",
    "determination",
]


def _load_local_env_file() -> None:
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return

    for raw in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip().lstrip("\ufeff")
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().lstrip("\ufeff")
        value = value.strip().strip("\"").strip("'")
        if key and not os.getenv(key):
            os.environ[key] = value


_load_local_env_file()


def _read_dotenv_value(target_key: str) -> str:
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return ""

    for raw in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip().lstrip("\ufeff")
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().lstrip("\ufeff")
        if key == target_key:
            return value.strip().strip("\"").strip("'")
    return ""


def _get_setting(key: str) -> str:
    value = os.getenv(key, "").strip()
    if value:
        return value
    return _read_dotenv_value(key).strip()


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/media/{file_id}")
def get_media(file_id: str) -> FileResponse:
    file_path = UPLOAD_DIR / f"{file_id}.wav"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(path=file_path, media_type="audio/wav", filename=file_path.name)


@app.post("/analyze")
def analyze(file: UploadFile = File(...)) -> Dict[str, Any]:
    public_base_url = _get_setting("PUBLIC_BASE_URL").rstrip("/")
    if not public_base_url:
        raise HTTPException(
            status_code=500,
            detail="PUBLIC_BASE_URL is required and must be a public URL reachable by Hume",
        )

    hume_api_key = _get_setting("HUME_API_KEY")
    if not hume_api_key:
        raise HTTPException(status_code=500, detail="HUME_API_KEY is required")

    _validate_wav(file)

    file_id = uuid.uuid4().hex
    file_path = UPLOAD_DIR / f"{file_id}.wav"
    _save_upload(file, file_path)

    media_url = f"{public_base_url}/media/{file_id}"

    predictions: Any
    try:
        job_id = _start_hume_job(hume_api_key, media_url)
        _wait_until_done(hume_api_key, job_id)
        predictions = _get_predictions(hume_api_key, job_id)
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Hume request failed: {exc}") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        _safe_delete_file(file_path)

    emotions = _extract_emotions(predictions)
    target_emotions = _select_target_emotions(emotions, TARGET_EMOTION_KEYS)
    transcript, transcript_segments = _extract_transcript(predictions)

    return {
        "file_id": file_id,
        "raw_hume_job_id": job_id,
        "transcript": transcript,
        "transcript_segments": transcript_segments,
        "emotions": target_emotions,
    }


def _validate_wav(file: UploadFile) -> None:
    filename = (file.filename or "").lower()
    content_type = (file.content_type or "").lower()

    has_wav_ext = filename.endswith(".wav")
    has_wav_mime = content_type in WAV_MIME_TYPES

    if not (has_wav_ext or has_wav_mime):
        raise HTTPException(status_code=400, detail="Only wav files are supported")


def _save_upload(file: UploadFile, destination: Path) -> None:
    with destination.open("wb") as out:
        while True:
            chunk = file.file.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)


def _safe_delete_file(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except Exception:
        # Cleanup should not break API behavior.
        pass


def _headers(api_key: str) -> Dict[str, str]:
    return {
        "X-Hume-Api-Key": api_key,
        "Content-Type": "application/json",
    }


def _start_hume_job(api_key: str, media_url: str) -> str:
    payload = {
        "urls": [media_url],
        "models": {
            "prosody": {
                "granularity": "utterance",
            }
        },
        "transcription": {
            "language": "en",
            "confidence_threshold": 0.0,
        },
    }

    response = requests.post(
        f"{HUME_API_BASE}/batch/jobs",
        headers=_headers(api_key),
        json=payload,
        timeout=30,
    )

    if response.status_code >= 400:
        raise RuntimeError(f"Hume start job failed ({response.status_code}): {response.text}")

    data = response.json()
    job_id = data.get("job_id")
    if not isinstance(job_id, str) or not job_id:
        raise RuntimeError("Hume start job response missing job_id")
    return job_id


def _wait_until_done(api_key: str, job_id: str) -> None:
    deadline = time.time() + HUME_JOB_TIMEOUT_SECONDS
    while time.time() < deadline:
        response = requests.get(
            f"{HUME_API_BASE}/batch/jobs/{job_id}",
            headers={"X-Hume-Api-Key": api_key},
            timeout=30,
        )

        if response.status_code >= 400:
            raise RuntimeError(f"Hume job status failed ({response.status_code}): {response.text}")

        payload = response.json()
        status = (
            payload.get("state", {}).get("status")
            or payload.get("status")
            or payload.get("job_status")
        )
        status = str(status).upper() if status else ""

        if status == "COMPLETED":
            return
        if status == "FAILED":
            raise RuntimeError(f"Hume job failed: {payload}")

        time.sleep(HUME_POLL_INTERVAL_SECONDS)

    raise RuntimeError(f"Hume job polling timed out after {HUME_JOB_TIMEOUT_SECONDS} seconds")


def _get_predictions(api_key: str, job_id: str) -> Any:
    response = requests.get(
        f"{HUME_API_BASE}/batch/jobs/{job_id}/predictions",
        headers={"X-Hume-Api-Key": api_key},
        timeout=30,
    )

    if response.status_code >= 400:
        raise RuntimeError(f"Hume predictions failed ({response.status_code}): {response.text}")

    return response.json()


def _extract_emotions(predictions: Any) -> List[Dict[str, float]]:
    extracted: List[Dict[str, float]] = []

    for node in _walk_nodes(predictions):
        emotions = node.get("emotions")
        if isinstance(emotions, list):
            for emo in emotions:
                if not isinstance(emo, dict):
                    continue
                name = emo.get("name")
                score = emo.get("score")
                if isinstance(name, str) and isinstance(score, (int, float)):
                    extracted.append({"name": name, "score": float(score)})

    merged: Dict[str, float] = {}
    counts: Dict[str, int] = {}

    for item in extracted:
        key = item["name"].strip()
        if not key:
            continue
        merged[key] = merged.get(key, 0.0) + item["score"]
        counts[key] = counts.get(key, 0) + 1

    averaged = [
        {"name": name, "score": (merged[name] / counts[name])}
        for name in merged.keys()
        if counts[name] > 0
    ]
    return averaged


def _extract_transcript(predictions: Any) -> tuple[str, List[Dict[str, Any]]]:
    segments: List[Dict[str, Any]] = []
    seen: set[tuple[str, float | None, float | None]] = set()

    for node in _walk_nodes(predictions):
        text = node.get("text")
        if not isinstance(text, str):
            continue

        cleaned_text = text.strip()
        if not cleaned_text:
            continue

        begin: float | None = None
        end: float | None = None
        time_info = node.get("time")
        if isinstance(time_info, dict):
            if isinstance(time_info.get("begin"), (int, float)):
                begin = float(time_info["begin"])
            if isinstance(time_info.get("end"), (int, float)):
                end = float(time_info["end"])

        unique_key = (cleaned_text, begin, end)
        if unique_key in seen:
            continue
        seen.add(unique_key)

        segment: Dict[str, Any] = {"text": cleaned_text}
        if begin is not None:
            segment["begin"] = begin
        if end is not None:
            segment["end"] = end

        confidence = node.get("confidence")
        if isinstance(confidence, (int, float)):
            segment["confidence"] = float(confidence)

        segments.append(segment)

    segments.sort(key=lambda s: (s.get("begin", float("inf")), s["text"]))
    transcript = " ".join(segment["text"] for segment in segments).strip()
    return transcript, segments


def _walk_nodes(node: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk_nodes(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_nodes(item)


def _select_target_emotions(emotions: List[Dict[str, float]], targets: List[str]) -> Dict[str, float]:
    score_map = {item["name"].strip().lower(): item["score"] for item in emotions}
    return {key: float(score_map.get(key, 0.0)) for key in targets}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="0.0.0.0", port=19000, reload=True)
