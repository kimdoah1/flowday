"""Basic events CRUD following Flowday_Team_Development_Guide chapter 3."""
from datetime import datetime, date
from typing import Literal
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, model_validator, ValidationError
from ..db import connect

router = APIRouter(prefix='/api/events', tags=['events'])
EventSource = Literal['manual','ai_plan','meeting','discord']

class EventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    start_at: datetime
    end_at: datetime
    source: EventSource = 'manual'
    memo: str = ''
    done: bool = False

    @model_validator(mode='after')
    def valid_interval(self):
        if self.start_at.tzinfo is None or self.end_at.tzinfo is None:
            raise ValueError('ISO8601 timezone offset is required')
        if self.end_at <= self.start_at:
            raise ValueError('end_at must be later than start_at')
        return self

class EventPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    start_at: datetime | None = None
    end_at: datetime | None = None
    source: EventSource | None = None
    memo: str | None = None
    done: bool | None = None

def find_one(conn, event_id: int):
    value = conn.execute('SELECT * FROM events WHERE event_id=%s FOR UPDATE', (event_id,)).fetchone()
    if not value:
        raise HTTPException(404, detail='Event not found')
    return value

@router.get('')
def list_events(start: date | None = None, end: date | None = None):
    query = 'SELECT * FROM events WHERE TRUE'
    params = []
    if start:
        query += ' AND start_at::date >= %s::date'; params.append(start)
    if end:
        query += ' AND start_at::date <= %s::date'; params.append(end)
    query += ' ORDER BY start_at, event_id'
    with connect() as conn:
        return {'events': conn.execute(query, params).fetchall()}

@router.post('', status_code=status.HTTP_201_CREATED)
def create_event(item: EventCreate):
    data = item.model_dump()
    with connect() as conn:
        return conn.execute('''
          INSERT INTO events(title,start_at,end_at,source,memo,done)
          VALUES(%(title)s,%(start_at)s,%(end_at)s,%(source)s,%(memo)s,%(done)s)
          RETURNING *
        ''', data).fetchone()

@router.patch('/{event_id}')
def patch_event(event_id: int, patch: EventPatch):
    changes = patch.model_dump(exclude_unset=True)
    if any(v is None for v in changes.values()):
        raise HTTPException(422, detail='Null updates are not supported')
    with connect() as conn:
        old = find_one(conn,event_id)
        if not changes:return old
        merged = dict(old); merged.update(changes)
        try:
            EventCreate(**{key: merged[key] for key in ['title','start_at','end_at','source','memo','done']})
        except ValidationError:
            raise HTTPException(422, detail='Invalid event interval or fields')
        allowed = ['title','start_at','end_at','source','memo','done']
        fields = [field for field in allowed if field in changes]
        expression = ', '.join(f'{field} = %s' for field in fields)
        values = [changes[field] for field in fields] + [event_id]
        return conn.execute(f'UPDATE events SET {expression} WHERE event_id = %s RETURNING *',values).fetchone()

@router.delete('/{event_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_event(event_id: int):
    with connect() as conn:
        found = conn.execute('DELETE FROM events WHERE event_id=%s RETURNING event_id',(event_id,)).fetchone()
        if not found:raise HTTPException(404,detail='Event not found')
    return None
