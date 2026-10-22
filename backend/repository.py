"""SQLite persistence behind an interchangeable repository protocol."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
from typing import Protocol

SOURCE_ROOT = Path(__file__).resolve().parents[1]


class Conflict(Exception):
    """An event identity or incident ID was reused with different content."""


class Repository(Protocol):
    def initialize(self) -> None: ...
    def check(self) -> None: ...
    def ingest(self, incident: dict) -> tuple[dict, bool]: ...
    def get(self, incident_id: str) -> dict | None: ...
    def save_investigation(self, result: dict, trace: dict) -> None: ...


def encode(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True,
                      separators=(',', ':'), allow_nan=False)


def event_content(incident):
    # Original incident ID is preserved. A repeated delivery may carry a new ID.
    return {k: v for k, v in incident.items()
            if k not in {'incident_id', 'ingestion_kind', 'raw_event_ref'}}


class SQLiteRepository:
    def __init__(self, runtime_dir: Path):
        self.runtime_dir = Path(runtime_dir).absolute()
        self.path = self.runtime_dir / 'cybersoc.sqlite3'

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=2)
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    def initialize(self):
        resolved = self.runtime_dir.resolve()
        if resolved.is_relative_to(SOURCE_ROOT) or self.runtime_dir.is_symlink():
            raise ValueError('Runtime directory must be outside the source tree')
        self.runtime_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        info = self.runtime_dir.stat()
        if info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError('Runtime directory must be private and owned by the service')
        if self.path.is_symlink():
            raise ValueError('Database symlinks are not allowed')
        with self.connection() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    source_event_id TEXT NOT NULL,
                    event_content TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    UNIQUE(source, source_event_id)
                );
                CREATE TABLE IF NOT EXISTS deliveries (
                    id INTEGER PRIMARY KEY,
                    incident_id TEXT NOT NULL REFERENCES incidents(incident_id),
                    received_at TEXT NOT NULL,
                    metadata TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS investigations (
                    investigation_id TEXT PRIMARY KEY,
                    incident_id TEXT NOT NULL REFERENCES incidents(incident_id),
                    trace_id TEXT NOT NULL UNIQUE,
                    result TEXT NOT NULL,
                    trace TEXT NOT NULL
                );
            ''')
        self.path.chmod(0o600)

    def check(self):
        with self.connection() as db:
            db.execute('SELECT incident_id FROM incidents LIMIT 1').fetchone()

    def ingest(self, incident):
        canonical = encode(event_content(incident))
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT event_content, payload FROM incidents '
                             'WHERE source=? AND source_event_id=?',
                             (incident['source'], incident['source_event_id'])).fetchone()
            if row:
                if row[0] != canonical:
                    raise Conflict()
                stored, created = json.loads(row[1]), False
            else:
                stored, created = incident, True
                try:
                    db.execute('INSERT INTO incidents VALUES (?, ?, ?, ?, ?)',
                               (incident['incident_id'], incident['source'],
                                incident['source_event_id'], canonical, encode(incident)))
                except sqlite3.IntegrityError as exc:
                    raise Conflict() from exc
            metadata = {k: incident[k] for k in ('ingestion_kind', 'raw_event_ref')
                        if k in incident}
            db.execute('INSERT INTO deliveries(incident_id, received_at, metadata) '
                       'VALUES (?, ?, ?)', (stored['incident_id'],
                       datetime.now(timezone.utc).isoformat(), encode(metadata)))
        return stored, created

    def get(self, incident_id):
        with self.connection() as db:
            row = db.execute('SELECT payload FROM incidents WHERE incident_id=?',
                             (incident_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def save_investigation(self, result, trace):
        with self.connection() as db:
            db.execute('INSERT INTO investigations VALUES (?, ?, ?, ?, ?)',
                       (result['investigation_id'], result['incident_id'],
                        trace['trace_id'], encode(result), encode(trace)))
