"""Google Gemini 호출 (무료 등급 사용 가능).

GEMINI_API_KEY는 https://aistudio.google.com/apikey 에서 무료로 발급받는다.
analyzer.py는 이 클라이언트의 extract()만 호출한다.
"""
import asyncio
import json
import os

import httpx

GEMINI_URL = "https://generativelanguage.googleapis.com"
DEFAULT_MODEL = "gemini-2.5-flash"  # 바뀌었으면 .env의 LLM_MODEL로 지정


class LLMError(Exception):
    """AI 모델을 쓸 수 없을 때 (키 오류, 한도 초과, 응답 형식 오류 등)."""


def parse_json(content: str) -> dict:
    """모델 응답에서 JSON 객체를 꺼낸다. 앞뒤에 군더더기가 붙어도 {...} 부분만 읽는다."""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start, end = content.find("{"), content.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(content[start : end + 1])
            except json.JSONDecodeError:
                pass
    raise LLMError("AI 응답을 JSON으로 읽지 못했어요.")


def to_gemini_schema(schema: dict) -> dict:
    """JSON 스키마 → Gemini responseSchema (type을 대문자로, 지원하는 키만 남긴다)."""
    out: dict = {}
    if "type" in schema:
        out["type"] = str(schema["type"]).upper()
    if "description" in schema:
        out["description"] = schema["description"]
    if "properties" in schema:
        out["properties"] = {k: to_gemini_schema(v) for k, v in schema["properties"].items()}
    if "items" in schema:
        out["items"] = to_gemini_schema(schema["items"])
    if "required" in schema:
        out["required"] = list(schema["required"])
    return out


def gemini_text(data: dict) -> str:
    """generateContent 응답에서 답변 텍스트를 꺼낸다 (생각 과정 파트는 제외)."""
    block = (data.get("promptFeedback") or {}).get("blockReason")
    if block:
        raise LLMError(f"Gemini가 요청을 차단했어요 ({block}).")
    candidates = data.get("candidates") or []
    if not candidates:
        raise LLMError("Gemini 응답이 비어 있어요.")
    parts = (candidates[0].get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
    if not text.strip():
        raise LLMError("Gemini 응답에 내용이 없어요.")
    return text


class GeminiClient:
    def __init__(self, api_key: str | None = None, timeout: float = 60):
        key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
        self.http = httpx.AsyncClient(
            base_url=GEMINI_URL,
            timeout=timeout,
            headers={"x-goog-api-key": key},  # 키는 URL이 아니라 헤더로 보낸다 (로그에 남지 않게)
        )

    async def check(self, model: str) -> str | None:
        """시작할 때 API 키와 모델 이름이 맞는지 확인한다. 문제가 있으면 안내 문구를, 정상이면 None."""
        try:
            res = await self.http.get(f"/v1beta/models/{model}")
        except httpx.HTTPError:
            return "Gemini 서버에 연결할 수 없어요. 인터넷 연결을 확인하세요."
        if res.status_code in (400, 401, 403):
            return "GEMINI_API_KEY가 올바른지 확인하세요."
        if res.status_code == 404:
            return f"모델 '{model}'을(를) 찾을 수 없어요. AI Studio의 모델 목록을 보고 LLM_MODEL을 바꾸세요."
        return None

    async def extract(self, model: str, system: str, user: str, schema: dict) -> dict:
        """schema 형식의 JSON으로만 답하게 해서 dict로 돌려준다."""
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
                "responseSchema": to_gemini_schema(schema),
            },
        }
        res = None
        for attempt in range(2):  # 무료 등급은 분당 한도가 있어서 한 번만 잠깐 기다렸다 재시도
            try:
                res = await self.http.post(f"/v1beta/models/{model}:generateContent", json=body)
            except httpx.HTTPError as e:
                raise LLMError("Gemini 서버에 연결할 수 없어요.") from e
            if res.status_code in (429, 503) and attempt == 0:
                await asyncio.sleep(5)
                continue
            break
        if res.status_code == 429:
            raise LLMError("Gemini 무료 사용량 한도에 걸렸어요. 잠시 후 다시 시도해 주세요.")
        if res.status_code in (400, 401, 403):
            raise LLMError("Gemini 요청이 거부됐어요. GEMINI_API_KEY와 모델 이름을 확인하세요.")
        if res.status_code == 404:
            raise LLMError(f"Gemini 모델 '{model}'을(를) 찾을 수 없어요.")
        if res.status_code >= 400:
            raise LLMError(f"Gemini 오류: {res.status_code}")
        return parse_json(gemini_text(res.json()))

    async def aclose(self):
        await self.http.aclose()
