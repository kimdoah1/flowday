"""api가 아직 없을 때 쓰는 가짜 서버 (표준 라이브러리만 사용, 설치 불필요).

실행:  python mock_server.py          → http://localhost:8000
봇 연결: API_URL=http://localhost:8000 (.env 또는 환경 변수)

- POST /api/ai/extract : "점심" 이 들어가면 {"events": []}, 아니면 base_date+2일 14:00 '팀 회의' 1개
- POST /api/proposals  : 새 external_id면 201 {"proposal_id", "status":"pending"}, 중복이면 409
- GET  /api/proposals  : pending 후보 목록
모두 명세서 3장 JSON 형식 그대로다.
"""
import json
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer

PROPOSALS: dict[str, dict] = {}  # external_id → 후보


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: dict):
        data = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        if self.path == "/api/health":
            self._send(200, {"status": "ok"})
        elif self.path == "/api/proposals":
            self._send(200, {"proposals": list(PROPOSALS.values())})
        else:
            self._send(404, {"detail": "not found"})

    def do_POST(self):
        body = self._body()
        if self.path == "/api/ai/extract":
            if "점심" in body.get("text", ""):
                return self._send(200, {"events": []})
            day = date.fromisoformat(body["base_date"]) + timedelta(days=2)
            self._send(200, {"events": [{
                "title": "팀 회의",
                "start_at": f"{day}T14:00:00+09:00",
                "end_at": f"{day}T15:00:00+09:00",
            }]})
        elif self.path == "/api/proposals":
            ext = body["external_id"]
            if ext in PROPOSALS:
                return self._send(409, {"detail": "duplicate external_id"})
            proposal_id = len(PROPOSALS) + 1
            PROPOSALS[ext] = {**body, "proposal_id": proposal_id, "status": "pending"}
            self._send(201, {"proposal_id": proposal_id, "status": "pending"})
        else:
            self._send(404, {"detail": "not found"})

    def log_message(self, fmt, *args):
        print(self.command, self.path, "→", fmt % args)


if __name__ == "__main__":
    print("Mock API 실행 중: http://localhost:8000")
    HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
