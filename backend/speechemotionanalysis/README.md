# Speech Emotion Analysis (Hume Prosody)

## 개요

이 서비스는 **WAV 파일 1개**를 받아 Hume prosody API로 분석하고, **전사(STT)** 텍스트와 지정한 **감정 지표** 점수를 반환합니다.  
Applogize Ren'Py 게임의 Stage 1 음성 인식/감정 분석에 사용됩니다.

---

## 사전 요구사항

- **Python 3.9+**
- **Hume API 키** — [Hume AI](https://www.hume.ai/)에서 발급
- (선택) Ren'Py 8.5+ — 게임 실행 시

---

## 1. 세팅 (처음 한 번만)

### 1.1 폴더로 이동

```bash
# macOS / Linux
cd /path/to/USU2026/applogize/backend/speechemotionanalysis

# Windows (PowerShell)
cd C:\path\to\USU2026\applogize\backend\speechemotionanalysis
```

### 1.2 패키지 설치

```bash
pip install -r requirements.txt
# 또는
python3 -m pip install -r requirements.txt
```

가상환경을 쓰는 경우:

```bash
python3 -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

### 1.3 환경 변수 설정

1. `.env.example`을 복사해 `.env` 생성:

   ```bash
   cp .env.example .env
   ```

2. `.env`를 열어 **HUME_API_KEY**만 반드시 넣기:

   ```env
   HUME_API_KEY=여기에_발급받은_키_입력
   ```

   - `PUBLIC_BASE_URL`은 현재 **/analyze 동작에는 사용하지 않습니다.** (파일을 Hume에 직접 업로드하므로 ngrok 없이 동작)

---

## 2. 서버 실행

기본 포트 **19000**으로 실행:

```bash
python3 -m uvicorn server:app --host 0.0.0.0 --port 19000
```

정상이면 다음처럼 뜹니다:

```text
INFO:     Uvicorn running on http://0.0.0.0:19000 (Press CTRL+C to quit)
```

- **중지:** 터미널에서 `Ctrl+C`

---

## 3. Ren'Py 게임에서 사용 (Applogize)

1. **백엔드 서버가 19000 포트에서 떠 있어야 합니다.** (위 2번 실행 유지)
2. 게임 실행:
   - **macOS:** 터미널에서 **가상환경 비활성화** 후 실행하는 것을 권장 (venv 활성화 시 Ren'Py가 잘못된 Python을 참조할 수 있음)
     ```bash
     deactivate   # venv 쓰고 있었다면
     cd /path/to/USU2026/applogize/renpy
     ./renpy.sh Applogize
     ```
   - 또는 Ren'Py 런처에서 프로젝트 `Applogize` 선택 후 실행
3. 게임 내 Stage 1에서 **Record (voice)** 로 녹음하면, 녹음 파일이 이 서버의 `/analyze`로 전송되고, 전사 결과가 텍스트로 표시됩니다.
4. **STT 언어:** 서버는 Hume 전사를 **영어(`en`)만** 사용하도록 설정되어 있습니다.

---

## 4. 동작 확인 (curl)

서버가 떠 있는 상태에서:

```bash
curl -X POST "http://127.0.0.1:19000/analyze" -F "file=@경로/파일.wav"
```

WAV는 16kHz 모노 16bit PCM을 권장합니다.  
정상이면 JSON으로 `transcript`, `emotions` 등이 내려옵니다.

---

## 5. API 요약

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/health` | 서버 상태 확인 |
| POST | `/analyze` | WAV 파일 1개 업로드 → 전사 + 감정 분석 결과 반환 |

### POST /analyze 요청

- **Content-Type:** `multipart/form-data`
- **필드:** `file` — WAV 파일

### POST /analyze 응답 예시

```json
{
  "file_id": "string",
  "raw_hume_job_id": "string",
  "transcript": "전사된 문장",
  "transcript_segments": [
    { "text": "string", "begin": 0.0, "end": 0.0, "confidence": 0.0 }
  ],
  "emotions": {
    "calmness": 0.0,
    "relief": 0.0,
    "contentment": 0.0,
    "love": 0.0,
    "sympathy": 0.0,
    "romance": 0.0,
    "anger": 0.0,
    "contempt": 0.0,
    "disgust": 0.0,
    "distress": 0.0,
    "sadness": 0.0,
    "disappointment": 0.0,
    "guilt": 0.0,
    "shame": 0.0,
    "interest": 0.0,
    "determination": 0.0
  }
}
```

---

## 6. 폴더/파일 구성

| 항목 | 역할 |
|------|------|
| `server.py` | FastAPI 앱, `/health`, `/analyze` 등 |
| `requirements.txt` | Python 의존성 |
| `.env.example` | 환경 변수 템플릿 (복사해 `.env` 생성) |
| `.env` | 실제 키 (git 제외, 공유 금지) |
| `run_server.ps1` | Windows용 서버 실행 보조 스크립트 (포트 정리 후 uvicorn) |
| `uploads/` | 분석 시 임시 업로드 저장, 완료 후 삭제 (git 제외) |

---

## 7. ngrok

- **/analyze** 는 클라이언트가 WAV를 서버로 보내고, 서버가 Hume에 **파일을 직접 업로드**하므로 **ngrok 없이** 로컬(`http://localhost:19000`)만으로 동작합니다.
- 다른 용도로 공개 URL이 필요할 때만 ngrok 등을 사용하면 됩니다.

---

## 8. 협업 시 참고

- `.env`, `uploads/`, `__pycache__/` 는 git에서 제외합니다.
- `.env.example` 만 공유하고, **HUME_API_KEY** 등 실제 값은 공유하지 않습니다.
- 기본 포트 **19000** 으로 통일해 두었습니다.
