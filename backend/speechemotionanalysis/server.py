import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

import requests
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from openai import OpenAI

app = FastAPI(title="Applogize Hume Bridge")

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

HUME_API_BASE = "https://api.hume.ai/v0"
HUME_JOB_TIMEOUT_SECONDS = 60
HUME_POLL_INTERVAL_SECONDS = 1

# Story reason for Stage 1 answer evaluation
CORRECT_REASON = "She had a dream where her boyfriend cheated on her."
OPENAI_MODEL = "gpt-4o-mini"

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


class CheckAnswerRequest(BaseModel):
    answer: str
    emotions: Dict[str, float] = {}
    wrong_attempt_count: int = 0  # 틀린 횟수 (힌트 강도 조절)


class EvaluateApologyFace(BaseModel):
    smile_count: int = 0
    smile: float = 0.0
    lookAway: float = 0.0
    sadness: float = 0.0


class EvaluateApologyRequest(BaseModel):
    transcript: str = ""
    voice_emotions: Dict[str, float] = {}
    face: Optional[EvaluateApologyFace] = None
    gesture: Optional[str] = None


@app.post("/check_answer")
def check_answer(body: CheckAnswerRequest) -> Dict[str, Any]:
    print(f"\n{'='*60}", flush=True)
    print(f"[check_answer] ▶ REQUEST", flush=True)
    print(f"[check_answer]   answer   : {body.answer!r}", flush=True)
    print(f"[check_answer]   wrong_attempt_count: {body.wrong_attempt_count}", flush=True)

    openai_api_key = _get_setting("OPENAI_API_KEY")
    if not openai_api_key:
        print("[check_answer] ✗ OPENAI_API_KEY not set", flush=True)
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is required")

    hint_strength = (
        "Give a GENTLE hint: mention one concept they're missing (dream OR cheating) "
        "without saying it directly. E.g. 'Think about what happens when I sleep.' or 'It's not about today.'"
        if body.wrong_attempt_count <= 1
        else "Give a STRONGER hint: nudge toward BOTH concepts. E.g. 'It wasn't real, but it felt real. And it was about us.'"
        if body.wrong_attempt_count == 2
        else "Give the STRONGEST hint short of the answer: almost spell it out. E.g. 'Something I dreamed. Something you did in that dream.'"
    )

    system_prompt = (
        "You are the judge of a couples' narrative game.\n\n"
        "Evaluate whether the player correctly identified the reason for the girlfriend's anger "
        "based solely on the text content of their answer. Ignore emotion scores.\n\n"
        "Evaluation rules:\n"
        "1. The core concept must be present: she had a DREAM in which her boyfriend CHEATED on her.\n"
        "2. Partial or paraphrased answers are acceptable as long as both elements "
        "(dream + cheating) are recognizable.\n\n"
        "Reply rules:\n"
        "- The 'reply' field MUST be written in ENGLISH. Short emotional dialogue (1-2 sentences) by the girlfriend.\n"
        "- correct=true: hurt but relieved he understood.\n"
        "- correct=false: dismissive or frustrated. Include a natural hint in the dialogue that helps the player "
        "get closer without giving the answer. "
        f"Hint strength (wrong_attempt_count={body.wrong_attempt_count}): {hint_strength}\n"
        "- The hint should feel like part of her emotional reaction, not a tutorial. "
        "E.g. 'That's not it. Maybe think about what I see when I close my eyes at night.'\n\n"
        "Respond ONLY with valid JSON, no markdown:\n"
        '{"correct": true, "reply": "..."}\n'
        'When correct=false, also include: "hint": "optional extra hint text" (short phrase, can repeat/clarify what she said)'
    )

    user_message = (
        f"Correct reason: {CORRECT_REASON}\n"
        f"Player's answer (speech-to-text): {body.answer}\n"
        f"Player has been wrong {body.wrong_attempt_count} time(s) so far."
    )

    print(f"[check_answer] → sending to OpenAI ({OPENAI_MODEL})", flush=True)
    print(f"[check_answer]   user_message:\n{user_message}", flush=True)

    try:
        client = OpenAI(api_key=openai_api_key)
        completion = client.chat.completions.create(
            model=OPENAI_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.8,
            timeout=25,
        )
        raw = completion.choices[0].message.content or "{}"
        print(f"[check_answer] ← OpenAI raw response: {raw}", flush=True)
        result = json.loads(raw)
        correct = bool(result.get("correct", False))
        reply = str(result.get("reply", "...")).strip()
        hint = str(result.get("hint", "")).strip() if not correct else ""
    except Exception as exc:
        logger.error("OpenAI check_answer failed: %s", exc)
        print(f"[check_answer] ✗ OpenAI error: {exc}", flush=True)
        raise HTTPException(status_code=502, detail=f"OpenAI request failed: {exc}") from exc

    print(f"[check_answer] ◀ RESPONSE  correct={correct}  reply={reply!r}  hint={hint!r}", flush=True)
    print(f"{'='*60}\n", flush=True)
    out = {"correct": correct, "reply": reply}
    if hint:
        out["hint"] = hint
    return out


@app.post("/evaluate_apology")
def evaluate_apology(body: EvaluateApologyRequest) -> Dict[str, Any]:
    """Stage 2: Evaluate apology sincerity from voice + face + gesture."""
    print(f"\n{'='*60}", flush=True)
    print(f"[evaluate_apology] ▶ REQUEST", flush=True)
    print(f"[evaluate_apology]   transcript: {body.transcript!r}", flush=True)
    print(f"[evaluate_apology]   voice_emotions: {body.voice_emotions}", flush=True)
    print(f"[evaluate_apology]   face: {body.face}", flush=True)
    print(f"[evaluate_apology]   gesture: {body.gesture!r}", flush=True)

    openai_api_key = _get_setting("OPENAI_API_KEY")
    if not openai_api_key:
        print("[evaluate_apology] ✗ OPENAI_API_KEY not set", flush=True)
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is required")

    face_str = "N/A"
    if body.face is not None:
        face_str = (
            f"smile_count={body.face.smile_count}, smile={body.face.smile:.2f}, "
            f"lookAway={body.face.lookAway:.2f}, sadness={body.face.sadness:.2f}"
        )
    voice_emotions_str = (
        ", ".join(f"{k}: {v:.2f}" for k, v in sorted(body.voice_emotions.items(), key=lambda x: -x[1]))
        if body.voice_emotions else "N/A"
    )

    system_prompt = (
        "You are the judge of a couples' apology game (Stage 2).\n\n"
        "Evaluate whether the player's apology should be ACCEPTED based on a holistic assessment of:\n"
        "1. **Voice transcript**: What they said. Sincere apologies acknowledge wrongdoing specifically.\n"
        "2. **Voice emotions**: Tone/sentiment from speech (sadness, guilt, sincerity good; anger, contempt bad).\n"
        "3. **Face**: smile_count high during apology = inappropriate (smiling when apologizing is bad). "
        "lookAway high = not making eye contact (bad). sadness = appropriate remorse.\n"
        "4. **Gesture**: TWO_HAND_HEART or OPEN_PALM can show sincerity. THUMBS_UP during apology may seem casual.\n\n"
        "If transcript is empty or face/gesture data is missing, weigh what you have. Missing data is not automatically bad.\n\n"
        "Reply rules (CRITICAL – make each reply feel unique):\n"
        "- The 'reply' field MUST be written in ENGLISH.\n"
        "- Short emotional dialogue (1–2 sentences) spoken BY THE GIRLFRIEND.\n"
        "- **React directly to what the player said.** Reference or echo specific words/phrases from their apology when natural. "
        "E.g. if they mention 'anniversary', 'dream', or 'trip', weave that into her reaction.\n"
        "- **Vary the response every time.** Avoid generic lines like 'I forgive you.' Create distinct reactions: "
        "sarcastic relief, reluctant acceptance, genuine softening, cold dismissal, exasperated rejection, etc.\n"
        "- accept=true: she is moved or softening. Vary tone: relieved, still hurt but accepting, touched, surprised they finally got it.\n"
        "- accept=false: still hurt. Vary tone: dismissive, frustrated, unimpressed, sarcastic, disappointed, angry.\n"
        "- Match her reply to the quality of their apology: shallow apology → sharper rebuke; heartfelt but flawed → mixed reaction.\n\n"
        "Respond ONLY with valid JSON, no markdown:\n"
        '{"accept": true, "reply": "..."}'
    )

    user_parts = [
        f"Transcript: {body.transcript or '(empty)'}",
        f"Voice emotions: {voice_emotions_str}",
        f"Face: {face_str}",
        f"Gesture: {body.gesture or 'N/A'}",
    ]
    user_message = "\n".join(user_parts)

    print(f"[evaluate_apology] → sending to OpenAI ({OPENAI_MODEL})", flush=True)
    print(f"[evaluate_apology]   user_message:\n{user_message}", flush=True)

    try:
        client = OpenAI(api_key=openai_api_key)
        completion = client.chat.completions.create(
            model=OPENAI_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.9,
            timeout=25,
        )
        raw = completion.choices[0].message.content or "{}"
        print(f"[evaluate_apology] ← OpenAI raw response: {raw}", flush=True)
        result = json.loads(raw)
        accept = bool(result.get("accept", False))
        reply = str(result.get("reply", "...")).strip()
    except Exception as exc:
        logger.error("OpenAI evaluate_apology failed: %s", exc)
        print(f"[evaluate_apology] ✗ OpenAI error: {exc}", flush=True)
        raise HTTPException(status_code=502, detail=f"OpenAI request failed: {exc}") from exc

    print(f"[evaluate_apology] ◀ RESPONSE  accept={accept}  reply={reply!r}", flush=True)
    print(f"{'='*60}\n", flush=True)
    return {"accept": accept, "reply": reply}


@app.get("/media/{file_id}")
def get_media(file_id: str) -> FileResponse:
    file_path = UPLOAD_DIR / f"{file_id}.wav"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(path=file_path, media_type="audio/wav", filename=file_path.name)


@app.post("/analyze")
def analyze(file: UploadFile = File(...)) -> Dict[str, Any]:
    print(f"\n{'='*60}", flush=True)
    print(f"[analyze] ▶ REQUEST  filename={file.filename!r}  content_type={file.content_type!r}", flush=True)

    hume_api_key = _get_setting("HUME_API_KEY")
    if not hume_api_key:
        print("[analyze] ✗ HUME_API_KEY not set", flush=True)
        raise HTTPException(status_code=500, detail="HUME_API_KEY is required")

    _validate_wav(file)

    file_id = uuid.uuid4().hex
    file_path = UPLOAD_DIR / f"{file_id}.wav"
    _save_upload(file, file_path)
    wav_size_bytes = file_path.stat().st_size
    print(f"[analyze]   saved WAV  file_id={file_id}  size={wav_size_bytes} bytes", flush=True)

    predictions: Any
    try:
        print(f"[analyze] → submitting job to Hume...", flush=True)
        job_id = _start_hume_job_from_file(hume_api_key, file_path)
        print(f"[analyze]   Hume job_id={job_id}  waiting for completion...", flush=True)
        _wait_until_done(hume_api_key, job_id)
        print(f"[analyze]   Hume job done, fetching predictions...", flush=True)
        predictions = _get_predictions(hume_api_key, job_id)
    except requests.RequestException as exc:
        print(f"[analyze] ✗ Hume request error: {exc}", flush=True)
        raise HTTPException(status_code=502, detail=f"Hume request failed: {exc}") from exc
    except RuntimeError as exc:
        print(f"[analyze] ✗ Hume runtime error: {exc}", flush=True)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        _safe_delete_file(file_path)

    emotions = _extract_emotions(predictions)
    target_emotions = _select_target_emotions(emotions, TARGET_EMOTION_KEYS)
    transcript, transcript_segments = _extract_transcript(predictions)

    if transcript:
        logger.info("STT transcript: %s", transcript)
        print(f"[STT] transcript: {transcript!r}", flush=True)
    else:
        # Debug: why empty? Log predictions shape and any text nodes
        def _top_keys(obj: Any, depth: int = 0) -> str:
            if depth > 2:
                return "..."
            if isinstance(obj, dict):
                return "{" + ", ".join(f"{k!r}: {_top_keys(v, depth+1)}" for k, v in list(obj.items())[:5]) + "}"
            if isinstance(obj, list):
                return f"[{len(obj)} items]"
            return type(obj).__name__
        text_count = sum(1 for n in _walk_nodes(predictions) if isinstance((n.get("text") or n.get("transcript")), str) and str((n.get("text") or n.get("transcript")) or "").strip())
        top = list(predictions.keys())[:8] if isinstance(predictions, dict) else (f"list[{len(predictions)}]" if isinstance(predictions, list) else type(predictions).__name__)
        first_keys = []
        if isinstance(predictions, list) and predictions and isinstance(predictions[0], dict):
            first_keys = list(predictions[0].keys())[:15]
        logger.warning(
            "STT transcript empty. wav_size=%s, top=%s, first_keys=%s, nodes_with_text=%s",
            wav_size_bytes,
            top,
            first_keys,
            text_count,
        )
        print(
            f"[STT] transcript empty. wav_size={wav_size_bytes} bytes, top={top}, first_keys={first_keys}, nodes_with_text={text_count}",
            flush=True,
        )

    top_emotions = sorted(target_emotions.items(), key=lambda x: -x[1])[:5] if target_emotions else []
    print(f"[analyze] ◀ RESPONSE  transcript={transcript!r}", flush=True)
    print(f"[analyze]   top emotions: {top_emotions}", flush=True)
    print(f"{'='*60}\n", flush=True)
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
    }


def _start_hume_job_from_file(api_key: str, file_path: Path) -> str:
    """
    Start a new batch inference job by uploading a local media file (multipart).
    This avoids needing PUBLIC_BASE_URL / public URLs for Hume to fetch media.
    """
    payload = {
        "models": {
            "prosody": {
                "granularity": "utterance",
            }
        },
        # Force Hume transcription to use **English** only.
        "transcription": {
            "language": "en",
            "confidence_threshold": 0.0,
        },
    }

    with file_path.open("rb") as f:
        response = requests.post(
            f"{HUME_API_BASE}/batch/jobs",
            headers=_headers(api_key),
            files=[("file", (file_path.name, f, "audio/wav"))],
            data={"json": json.dumps(payload)},
            timeout=60,
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
    # First try: parse known Hume batch predictions structure (list -> results -> predictions -> models -> prosody -> grouped_predictions).
    # This is more reliable than generic tree-walk when response shape changes.
    if isinstance(predictions, list):
        hume_segments: List[Dict[str, Any]] = []
        for item in predictions:
            if not isinstance(item, dict):
                continue
            results = item.get("results")
            if not isinstance(results, dict):
                continue
            preds = results.get("predictions")
            if not isinstance(preds, list):
                continue
            for pred in preds:
                if not isinstance(pred, dict):
                    continue
                models = pred.get("models")
                if not isinstance(models, dict):
                    continue
                prosody = models.get("prosody")
                if not isinstance(prosody, dict):
                    continue
                grouped = prosody.get("grouped_predictions")
                if not isinstance(grouped, list):
                    continue
                for group in grouped:
                    if not isinstance(group, dict):
                        continue
                    gp = group.get("predictions")
                    if not isinstance(gp, list):
                        continue
                    for p in gp:
                        if not isinstance(p, dict):
                            continue
                        text = p.get("text") or p.get("transcript") or p.get("utterance")
                        if not isinstance(text, str):
                            continue
                        cleaned = text.strip()
                        if not cleaned:
                            continue
                        seg: Dict[str, Any] = {"text": cleaned}
                        # Some responses include time info at top-level or nested.
                        time_info = p.get("time") or p.get("timestamps") or p.get("timestamp")
                        if isinstance(time_info, dict):
                            if isinstance(time_info.get("begin"), (int, float)):
                                seg["begin"] = float(time_info["begin"])
                            if isinstance(time_info.get("end"), (int, float)):
                                seg["end"] = float(time_info["end"])
                        hume_segments.append(seg)

        if hume_segments:
            hume_segments.sort(key=lambda s: (s.get("begin", float("inf")), s["text"]))
            transcript = " ".join(s["text"] for s in hume_segments).strip()
            return transcript, hume_segments

    segments: List[Dict[str, Any]] = []
    seen: set[tuple[str, float | None, float | None]] = set()

    for node in _walk_nodes(predictions):
        text = node.get("text") or node.get("transcript")
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
