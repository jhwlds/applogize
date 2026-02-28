# Applogize Backend

실시간 분석을 위한 FastAPI 백엔드 서버

## 설치 방법

```bash
# 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
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

- `GET /` - 서버 상태 확인
- `GET /health` - 헬스 체크
- `GET /api/test` - API 테스트
- `POST /api/analyze` - 분석 엔드포인트 (나중에 구현)
- `WS /ws` - WebSocket 연결

## 프로젝트 구조

```
backend/
├── server.py              # 메인 서버
├── config.py              # 설정 파일
├── requirements.txt       # 의존성
├── .env                   # 환경 변수
├── routes/                # API 라우트
│   └── __init__.py
└── services/              # AI 서비스 (나중에 추가)
    └── __init__.py
```

## 나중에 추가할 기능

- 얼굴 모션 인식
- 시선 추적
- 음성 인식
- 음성 분석
