"""Requires an isolated PostgreSQL DATABASE_URL; CI supplies a service database."""
import os
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client(monkeypatch):
    if not os.getenv('DATABASE_URL'):
        pytest.skip('Set DATABASE_URL to an isolated PostgreSQL test database')
    monkeypatch.setenv('LLM_MODE', 'rule')
    with TestClient(app) as client:
        yield client

EVENT = dict(title='통합 테스트', start_at='2026-11-20T09:00:00+09:00',
             end_at='2026-11-20T10:00:00+09:00', source='manual', memo='test')

def test_crud_persistence_and_invalid_patch(client):
    assert client.get('/api/health').json() == {'status': 'ok'}
    response = client.post('/api/events', json=EVENT)
    assert response.status_code == 201
    event = response.json()
    eid = event['event_id']
    try:
        assert event['start_at'].endswith('+09:00')
        with TestClient(app) as reopened:
            assert eid in [e['event_id'] for e in reopened.get('/api/events').json()['events']]
        assert client.patch(f'/api/events/{eid}', json={'done': True}).json()['done']
        assert client.patch(f'/api/events/{eid}', json={'end_at': '2026-11-19T09:00:00+09:00'}).status_code == 422
        assert client.patch(f'/api/events/{eid}', json={'memo': None}).status_code == 422
        assert client.get('/api/events?start=not-a-date').status_code == 422
    finally:
        assert client.delete(f'/api/events/{eid}').status_code == 204
    assert client.delete(f'/api/events/{eid}').status_code == 404

def test_proposal_approval_is_explicit_and_idempotent(client):
    unique = uuid4().hex
    body = {**EVENT, 'title': unique, 'source': 'discord', 'external_id': unique, 'original_text': '회의'}
    response = client.post('/api/proposals', json=body)
    assert response.status_code == 201
    pid = response.json()['proposal_id']
    assert client.post('/api/proposals', json=body).status_code == 409
    assert not any(e['title'] == unique for e in client.get('/api/events').json()['events'])
    first = client.post(f'/api/proposals/{pid}/approve')
    assert first.status_code == 200
    second = client.post(f'/api/proposals/{pid}/approve')
    assert second.json()['event_id'] == first.json()['event_id']
    assert client.post(f'/api/proposals/{pid}/reject').status_code == 409
    assert pid not in [p['proposal_id'] for p in client.get('/api/proposals').json()['proposals']]
    assert client.delete(f"/api/events/{first.json()['event_id']}").status_code == 204
    assert client.post(f'/api/proposals/{pid}/approve').status_code == 409

def test_rejected_candidate_cannot_be_approved(client):
    body = {**EVENT, 'source': 'discord', 'external_id': uuid4().hex}
    pid = client.post('/api/proposals', json=body).json()['proposal_id']
    assert client.post(f'/api/proposals/{pid}/reject').json()['status'] == 'rejected'
    assert client.post(f'/api/proposals/{pid}/approve').status_code == 409

def test_plan_and_meeting_routes(client):
    request = dict(goal='팀 프로젝트', description='달력', start_date='2026-11-19', deadline='2026-11-25', intensity='balanced')
    plan = client.post('/api/ai/plan', json=request)
    assert plan.status_code == 200
    assert plan.json()['mode'] == 'rule'
    assert len(plan.json()['tasks']) == 3
    assert client.post('/api/ai/plan', json={**request, 'deadline': '2026-11-01'}).status_code == 422
    upload = client.post('/api/meetings', files={'file': ('meeting.txt', '11월 25일 오후 2시에 팀 회의'.encode())})
    assert upload.status_code == 201
    meeting = client.get(f"/api/meetings/{upload.json()['meeting_id']}").json()
    assert meeting['status'] == 'done'
    assert meeting['transcript'] == '11월 25일 오후 2시에 팀 회의'
    assert meeting['events']
