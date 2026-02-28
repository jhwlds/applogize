# Applogize Backend

실시간 분석을 위한 FastAPI 백엔드 서버

## 설치 방법

```bash
# 가상환경 생성 (권장)
python3.11 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

## 환경 설정

`.env` 파일을 생성하고 필요한 환경 변수를 설정하세요:

```bash
cp .env.example .env
```

`.env` 파일에 OpenAI API 키를 추가하세요:
```
OPENAI_API_KEY=your-actual-api-key-here
```

## 실행 방법

```bash
python server.py
```

또는

```bash
uvicorn server:app --reload
```

## API 문서

서버 실행 후 다음 주소에서 자동 생성된 API 문서를 확인할 수 있습니다:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 엔드포인트

### 기본
- `GET /` - 서버 상태 확인
- `GET /health` - 헬스 체크
- `GET /api/test` - API 테스트

### AI 채팅
- `POST /api/chat` - OpenAI를 사용한 채팅
  ```json
  {
    "message": "안녕"
  }
  ```
- `GET /api/chat/health` - 채팅 서비스 상태 확인

### 분석 (향후 구현)
- `POST /api/analyze` - 분석 엔드포인트

## 프로젝트 구조

```
backend/
├── server.py              # 메인 서버
├── config.py              # 설정 파일
├── requirements.txt       # 의존성
├── .env                   # 환경 변수 (git에서 제외)
├── .env.example           # 환경 변수 예시
├── models/                # 데이터 모델
│   ├── __init__.py
│   └── chat.py           # 채팅 요청/응답 모델
├── routes/                # API 라우트
│   ├── __init__.py
│   └── chat.py           # 채팅 API 엔드포인트
└── services/              # 비즈니스 로직
    ├── __init__.py
    └── openai_service.py  # OpenAI API 호출
```

## 나중에 추가할 기능

- 얼굴 모션 인식
- 시선 추적
- 음성 인식
- 음성 분석

## 테스트 방법

### curl로 테스트
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "안녕"}'
```

### Swagger UI로 테스트
1. http://localhost:8000/docs 접속
2. `POST /api/chat` 엔드포인트 선택
3. "Try it out" 클릭
4. 메시지 입력 후 "Execute" 클릭
