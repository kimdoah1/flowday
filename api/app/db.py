"""PostgreSQL connection helpers for the Flowday event contract."""
import os
import psycopg
from psycopg.rows import dict_row

URL = os.getenv('DATABASE_URL', 'postgresql://calendar:calendar@db:5432/calendar')

def connect():
    return psycopg.connect(URL, row_factory=dict_row, options="-c timezone=Asia/Seoul")

def initialize():
    with connect() as conn:
        conn.execute('''
          CREATE TABLE IF NOT EXISTS events (
            event_id BIGSERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            start_at TIMESTAMPTZ NOT NULL,
            end_at TIMESTAMPTZ NOT NULL,
            source TEXT NOT NULL DEFAULT 'manual',
            memo TEXT NOT NULL DEFAULT '',
            done BOOLEAN NOT NULL DEFAULT FALSE
          )
        ''')
        conn.execute('''
          CREATE TABLE IF NOT EXISTS proposals (
            proposal_id BIGSERIAL PRIMARY KEY,
            title TEXT NOT NULL, start_at TIMESTAMPTZ NOT NULL,
            end_at TIMESTAMPTZ NOT NULL, source TEXT NOT NULL,
            original_text TEXT NOT NULL DEFAULT '',
            external_id TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'pending',
            event_id BIGINT REFERENCES events(event_id) ON DELETE SET NULL
          )
        ''')
