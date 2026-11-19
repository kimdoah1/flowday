from datetime import date
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.routers import plan

app = FastAPI()
app.include_router(plan.router, prefix='/api')
client = TestClient(app)
GOAL = dict(goal='프로젝트', description='웹 앱', start_date='2026-11-19', deadline='2026-11-25', intensity='balanced')

def test_missing_key_is_not_mock_success(monkeypatch):
    monkeypatch.setenv('LLM_MODE', 'auto')
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    assert client.post('/api/ai/plan', json=GOAL).status_code == 503

def test_general_goal_calls_existing_llm(monkeypatch):
    monkeypatch.setenv('LLM_MODE', 'auto')
    monkeypatch.setenv('GEMINI_API_KEY', 'test-only')
    monkeypatch.setenv('LLM_MODEL', 'test-model')
    calls = []
    def fake(prompt, schema):
        calls.append(prompt)
        return schema(tasks=[dict(title=t, date='2026-11-20') for t in ['설계','구현','검증']])
    monkeypatch.setattr(plan, 'ask_llm', fake)
    response = client.post('/api/ai/plan', json=GOAL)
    assert response.status_code == 200
    assert response.json()['mode'] == 'llm'
    assert calls

def test_book_contract_still_uses_optimizer(monkeypatch):
    monkeypatch.setattr(plan, 'ask_llm', lambda prompt, schema: schema(tasks=[dict(title='읽기', pages_start=1, pages_end=10, estimated_minutes=20)]))
    response = client.post('/api/ai/plan', json=dict(goal='독서', start_date='2026-11-19', deadline='2026-11-20', book_name='교재', total_pages=10, available_minutes_per_day=30))
    assert response.status_code == 200
    task = response.json()['tasks'][0]
    assert task['pages_start'] == 1 and task['pages_end'] == 10
    assert date(2026,11,19) <= date.fromisoformat(task['date']) <= date(2026,11,20)

def test_invalid_book_does_not_become_general_goal():
    response = client.post('/api/ai/plan', json={**GOAL, 'book_name': '교재', 'total_pages': -1})
    assert response.status_code == 422
