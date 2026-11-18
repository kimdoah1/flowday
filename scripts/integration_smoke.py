"""Run through Nginx against a real API/DB. No LLM credentials required."""
import json
import os
import urllib.request
from uuid import uuid4

BASE = os.getenv('BASE_URL', 'http://localhost:8080')
def request(path, method='GET', body=None):
    req = urllib.request.Request(BASE + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as response:
        data = response.read()
        return json.loads(data) if data else None

def main():
    with urllib.request.urlopen(BASE) as response:
        assert b'<div id="root">' in response.read()
    assert request('/api/health') == {'status': 'ok'}
    payload = dict(title='smoke-' + uuid4().hex, start_at='2026-11-20T09:00:00+09:00',
                   end_at='2026-11-20T10:00:00+09:00', source='manual')
    event = request('/api/events', 'POST', payload)
    eid = event['event_id']
    try:
        assert any(e['event_id'] == eid for e in request('/api/events')['events'])
        assert request(f'/api/events/{eid}', 'PATCH', {'done': True})['done']
        proposal = request('/api/proposals', 'POST', {**payload, 'source': 'discord', 'external_id': uuid4().hex})
        path = f"/api/proposals/{proposal['proposal_id']}/approve"
        accepted = request(path, 'POST')
        assert request(path, 'POST')['event_id'] == accepted['event_id']
        request(f"/api/events/{accepted['event_id']}", 'DELETE')
    finally:
        request(f'/api/events/{eid}', 'DELETE')
    print('PASS: Nginx → API → PostgreSQL CRUD and proposal approval')

if __name__ == '__main__':
    main()
