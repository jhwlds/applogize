# FaceMotion tracker (Python sidecar)

Ren'Py 없이도 **웹캠 프리뷰 창(OpenCV)** 에서 아래 신호를 바로 확인할 수 있는 Python tracker입니다.

- Smile score (0~1)
- LookAway score (0~1) + LookingAway YES/NO (히스테리시스)
- Hand gesture: `OPEN_PALM` / `THUMBS_UP` / `—`
- Dialog line (짧은 문장, 너무 자주 바뀌지 않게 안정화)

추후 Ren'Py 연동 시에는 tracker가 출력하는 **stdout JSON Lines** 를 읽어서 게임 변수를 갱신하는 방식으로 붙이면 됩니다.

## 설치

```bash
cd tracker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows PowerShell:

```bash
cd tracker
python3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 실행

```bash
python3 tracker.py
```

처음 실행 시 모델(`.task`) 파일이 없으면 자동으로 다운로드해서 `tracker/models/`에 저장합니다.

## 키 조작

- `q` 또는 `esc`: 종료
- `d`: 디버그 HUD 토글
- `j`: JSON 출력 토글 (실행 중 ON/OFF)

## 옵션

```bash
# 카메라 인덱스 변경
python3 tracker.py --camera 1

# JSON Lines를 stdout으로 출력(나중에 Ren'Py가 읽을 용도)
python3 tracker.py --json

# JSON 출력 주기(Hz)
python3 tracker.py --json --json-rate-hz 10

# 손 트래킹 끄기
python3 tracker.py --no-hand

# 그림(랜드마크) 끄고 HUD만 보기(가벼움)
python3 tracker.py --no-draw-face --no-draw-hand
```

## JSON Lines 포맷(요약)

`--json`이 켜져 있으면 지정 주기마다 한 줄 JSON을 출력합니다.

예:

```json
{"ts":123.45,"smile":0.41,"lookAway":0.33,"lookingAway":false,"handPresent":true,"gesture":"THUMBS_UP","dialog":"..."}
```

## 문제 해결

- **카메라가 안 열림**: macOS는 터미널/IDE에 카메라 권한이 필요할 수 있습니다. (시스템 설정 → 개인 정보 보호 및 보안 → 카메라)
- **손이 느림**: 손 추론은 기본 80ms 간격으로만 돌립니다. 더 줄이려면 `--hand-interval-ms` 값을 키우세요.
- **성능이 너무 무거움**: `--no-draw-face --no-draw-hand`로 그림을 끄고 HUD만 보세요.

