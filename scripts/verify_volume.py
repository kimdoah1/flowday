"""Create a marker before recreation, then verify and delete it afterwards."""
import sys
from pathlib import Path
from integration_smoke import request

marker = Path(sys.argv[2])
if sys.argv[1] == 'create':
    event = request('/api/events', 'POST', dict(title='volume-verification',
        start_at='2026-11-20T09:00:00+09:00', end_at='2026-11-20T10:00:00+09:00'))
    marker.write_text(str(event['event_id']))
else:
    eid = int(marker.read_text())
    assert any(e['event_id'] == eid for e in request('/api/events')['events'])
    request(f'/api/events/{eid}', 'DELETE')
    print('PASS: PostgreSQL volume retained event across container recreation')
