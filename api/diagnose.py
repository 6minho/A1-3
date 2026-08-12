from http.server import BaseHTTPRequestHandler
import json
import os
import requests

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent"

PROMPT_TEMPLATE = """당신은 PC 하드웨어 병목 진단 전문가입니다.
아래 사양을 보고 병목을 진단하세요.

CPU: {cpu}
그래픽카드: {gpu}
RAM: {ram}
주 용도: {usage}

반드시 아래 JSON 형식으로만 응답하세요. 다른 설명이나 마크다운 코드블록은 절대 포함하지 마세요.

{{
  "bottleneck": "병목 부품명 (없으면 '없음')",
  "reason": "판정 이유 2문장",
  "score": 0~100 사이 정수 (해당 용도 적합도),
  "upgrades": [
    {{"part": "부품명", "why": "이유 1문장"}},
    {{"part": "부품명", "why": "이유 1문장"}},
    {{"part": "부품명", "why": "이유 1문장"}}
  ]
}}"""


class handler(BaseHTTPRequestHandler):
    def _send(self, status, payload):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(payload, ensure_ascii=False).encode('utf-8'))

    def do_GET(self):
        self._send(405, {"error": "POST 요청만 지원합니다."})

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length))
        except Exception:
            return self._send(400, {"error": "요청 형식이 올바르지 않습니다."})

        cpu = (body.get('cpu') or '').strip()
        gpu = (body.get('gpu') or '').strip()

        if not cpu or not gpu:
            return self._send(400, {"error": "CPU와 그래픽카드는 필수 입력값입니다."})

        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            return self._send(500, {"error": "서버 설정 오류입니다. 관리자에게 문의하세요."})

        prompt = PROMPT_TEMPLATE.format(
            cpu=cpu,
            gpu=gpu,
            ram=(body.get('ram') or '미입력').strip(),
            usage=(body.get('usage') or '미입력').strip(),
        )

        try:
            res = requests.post(
                API_URL,
                headers={
                    'Content-Type': 'application/json',
                    'x-goog-api-key': api_key,
                },
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.4,
                        "responseMimeType": "application/json",
                    },
                },
                timeout=25,
            )
        except requests.Timeout:
            return self._send(504, {"error": "AI 응답이 지연되고 있습니다. 잠시 후 다시 시도해주세요."})
        except Exception:
            return self._send(502, {"error": "AI 서버 연결에 실패했습니다."})

        if res.status_code == 429:
            return self._send(429, {"error": "요청이 많습니다. 잠시 후 다시 시도해주세요."})
        if res.status_code != 200:
            return self._send(502, {
                "error": "AI 서버 오류가 발생했습니다.",
                "debug": res.text[:800],
            })

        raw = res.text
        try:
            data = res.json()
            parts = data['candidates'][0]['content']['parts']
            text = ''.join(p.get('text', '') for p in parts if not p.get('thought'))
            result = json.loads(text)
            return self._send(200, result)
        except Exception as err:
            return self._send(502, {
                "error": "AI 응답을 해석하지 못했습니다.",
                "debug": raw[:800],
                "err_type": type(err).__name__,
            })