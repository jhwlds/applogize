# Stage 1 – Answer check API (voice guess)

The game sends the player’s answer (from voice STT or text input) to your server. The server decides if it’s correct or wrong.

## Endpoint

- **URL**: set in game with `answer_check_url` (default: `http://localhost:8000/check_answer`)
- **Method**: `POST`
- **Content-Type**: `application/json`

## Request body

```json
{ "answer": "I forgot our anniversary and booked a solo trip" }
```

`answer` is the string the player said (or typed). You can fix the “correct” answer on the server (e.g. compare to a reference string or use NLU).

## Response body

Return JSON with a single key `correct` (boolean):

- Correct: `{ "correct": true }`
- Wrong: `{ "correct": false }`

Any other shape or non-2xx response is treated as “server error” and the player sees a retry message.

## Example server (Python, Flask)

```python
from flask import Flask, request, jsonify

app = Flask(__name__)

# Fix the expected answer on the server (or use NLU)
CORRECT_ANSWER = "i forgot our anniversary and booked a solo trip"

@app.route("/check_answer", methods=["POST"])
def check_answer():
    data = request.get_json() or {}
    answer = (data.get("answer") or "").strip().lower()
    # Simple exact/similar check; replace with your logic
    correct = CORRECT_ANSWER in answer or answer in CORRECT_ANSWER
    return jsonify({"correct": correct})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
```

Run: `pip install flask && python server.py`. Then start the game and use “Submit to server” (or voice then submit).

## Voice (STT) on the client

- **Record** in the game uses the microphone and runs STT on the client (Google Web Speech via `SpeechRecognition`).
- Install: `pip install SpeechRecognition pyaudio` (and allow mic in OS).
- If STT isn’t available, the player can type the answer and still use “Submit to server”; the server contract is the same.
