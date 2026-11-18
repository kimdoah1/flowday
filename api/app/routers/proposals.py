"""Review candidates; only an explicit approval creates a calendar event."""
from typing import Literal
from fastapi import APIRouter, HTTPException
from pydantic import Field
from app.db import connect
from app.routers.events import EventCreate

router = APIRouter(prefix='/api/proposals', tags=['proposals'])

class ProposalCreate(EventCreate):
    source: Literal['discord'] = 'discord'
    original_text: str = ''
    external_id: str = Field(min_length=1, max_length=200)

@router.post('', status_code=201)
def create_proposal(body: ProposalCreate):
    with connect() as conn:
        row = conn.execute('''INSERT INTO proposals
          (title,start_at,end_at,source,original_text,external_id)
          VALUES (%(title)s,%(start_at)s,%(end_at)s,%(source)s,%(original_text)s,%(external_id)s)
          ON CONFLICT (external_id) DO NOTHING RETURNING proposal_id,status
        ''', body.model_dump()).fetchone()
        if row is None:
            raise HTTPException(409, 'Duplicate external_id')
        return row

@router.get('')
def list_proposals():
    with connect() as conn:
        return {'proposals': conn.execute("SELECT * FROM proposals WHERE status='pending' ORDER BY proposal_id").fetchall()}

def locked_proposal(conn, proposal_id):
    row = conn.execute('SELECT * FROM proposals WHERE proposal_id=%s FOR UPDATE', (proposal_id,)).fetchone()
    if row is None:
        raise HTTPException(404, 'Proposal not found')
    return row

@router.post('/{proposal_id}/approve')
def approve(proposal_id: int):
    with connect() as conn:
        row = locked_proposal(conn, proposal_id)
        if row['status'] == 'rejected':
            raise HTTPException(409, 'Proposal already rejected')
        if row['status'] == 'approved':
            event = conn.execute('SELECT * FROM events WHERE event_id=%s', (row['event_id'],)).fetchone()
            if event is None:
                raise HTTPException(409, 'Approved event was deleted')
            return event
        event = conn.execute('''INSERT INTO events (title,start_at,end_at,source,memo)
          VALUES (%(title)s,%(start_at)s,%(end_at)s,%(source)s,%(original_text)s) RETURNING *''', row).fetchone()
        conn.execute("UPDATE proposals SET status='approved',event_id=%s WHERE proposal_id=%s", (event['event_id'], proposal_id))
        return event

@router.post('/{proposal_id}/reject')
def reject(proposal_id: int):
    with connect() as conn:
        row = locked_proposal(conn, proposal_id)
        if row['status'] == 'approved':
            raise HTTPException(409, 'Proposal already approved')
        return conn.execute("UPDATE proposals SET status='rejected' WHERE proposal_id=%s RETURNING proposal_id,status", (proposal_id,)).fetchone()
