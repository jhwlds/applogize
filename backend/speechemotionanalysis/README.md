# Speech Emotion Analysis (Hume Prosody)

## 개요
이 서비스는 `wav` 파일 1개를 받아 Hume prosody 분석을 수행하고, 전사 텍스트와 지정한 감정 지표 점수를 반환합니다.

## 폴더 파일 구성 및 역할
- `server.py`
  - FastAPI 서버 메인 파일입니다.
  - 엔드포인트:
    - `GET /health`
    - `POST /analyze` (multipart `file`)
    - `GET /media/{file_id}` (Hume가 가져갈 임시 오디오 URL)
  - 처리 흐름:
    - wav 검증
    - 업로드 파일 임시 저장
    - Hume 배치 잡 생성
    - 완료될 때까지 폴링
    - 감정 점수 파싱
    - 지정 감정 키만 반환
    - 분석 후 임시 파일 삭제

- `requirements.txt`
  - Python 의존성 목록입니다.
  - 아래 명령으로 설치합니다:
  - `pip install -r requirements.txt`

- `.env.example`
  - 팀원이 복사해서 쓰는 환경변수 템플릿입니다.
  - `.env`로 복사 후 실제 값으로 채웁니다.

- `.env` (로컬 전용, git ignore)
  - 실제 시크릿/실행 값입니다.
  - 필수 키:
    - `HUME_API_KEY`
    - `PUBLIC_BASE_URL` (Hume가 접근 가능한 공개 URL, 예: ngrok URL)

- `run_server.ps1`
  - Windows용 서버 실행 보조 스크립트입니다.
  - 포트 충돌 프로세스를 정리한 뒤 uvicorn을 실행합니다.
  - 기본 포트는 `19000`이며, 점유 중이면 `19001`로 폴백합니다.

- `uploads/` (런타임 폴더, git ignore)
  - `/analyze` 처리 중 임시 업로드 파일이 저장됩니다.
  - 분석 완료 후 파일은 삭제됩니다.

## 현재 API 응답 형태
`POST /analyze`
```json
{
  "file_id": "string",
  "raw_hume_job_id": "string",
  "transcript": "string",
  "transcript_segments": [
    {
      "text": "string",
      "begin": 0.0,
      "end": 0.0,
      "confidence": 0.0
    }
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

## 설정 방법
1. 폴더 이동:
```powershell
cd c:\Users\minjo\GitHub\applogize\backend\speechemotionanalysis
```
2. 패키지 설치:
```powershell
pip install -r requirements.txt
```
3. 환경변수 파일 생성:
```powershell
copy .env.example .env
```
4. `.env` 수정:
- `HUME_API_KEY=...`
- `PUBLIC_BASE_URL=https://...` (ngrok/배포 도메인)

## ngrok 필요 여부
- Hume가 로컬 서버 파일을 가져가려면 공개 URL이 필요합니다.
- 로컬에서 실행할 때는 보통 `ngrok`(또는 유사 터널)이 필요합니다.
- 이미 퍼블릭으로 배포된 서버를 쓰는 경우엔 `ngrok`이 없어도 됩니다.

## ngrok 사용 방법 (로컬 실행 시)
1. 서버 실행:
```powershell
powershell -ExecutionPolicy Bypass -File .\run_server.ps1 -Port 19000
```
2. 별도 터미널에서 ngrok 실행:
```powershell
ngrok http 19000
```
3. ngrok가 표시한 `https://...` 주소를 `.env`의 `PUBLIC_BASE_URL`로 설정
4. 서버 재시작

## 실행 방법
방법 1:
```powershell
python -m uvicorn server:app --host 0.0.0.0 --port 19000 --env-file .env
```
방법 2 (보조 스크립트):
```powershell
powershell -ExecutionPolicy Bypass -File .\run_server.ps1 -Port 19000
```

## 테스트 요청

### m4a 파일을 wav로 변환하기
`/analyze`는 wav만 받기 때문에 m4a는 먼저 변환해야 합니다.

1. ffmpeg 설치 (Windows):
```powershell
winget install --id Gyan.FFmpeg -e
```

2. m4a -> wav 변환 (권장 포맷: 16kHz mono 16-bit PCM):
```powershell
ffmpeg -i .\uploads\{input 파일이름}.m4a -ac 1 -ar 16000 -sample_fmt s16 .\uploads\{output 파일이름}.wav
```

### 변환된 wav로 분석 요청
```powershell
curl.exe -X POST "http://127.0.0.1:19000/analyze" -F "file=@C:\Users\minjo\GitHub\applogize\backend\speechemotionanalysis\uploads\2.wav"
```

## 협업 시 참고
- `.env`, `uploads/`, `__pycache__/`는 git에서 제외됩니다.
- `.env.example`만 공유하고 실제 API 키는 공유하지 않습니다.
- 기본 포트는 19000으로 통일합니다.
