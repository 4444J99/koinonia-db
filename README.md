# koinonia-db

Shared database models, migrations, and seed data for all ORGAN-VI Koinonia repositories.

[![CI](https://github.com/4444J99/koinonia-db/actions/workflows/ci.yml/badge.svg)](https://github.com/4444J99/koinonia-db/actions/workflows/ci.yml)

## Overview

koinonia-db is the single source of truth for ORGAN-VI's PostgreSQL schema. It provides SQLAlchemy ORM models consumed by salon-archive, reading-group-curriculum, adaptive-personal-syllabus, and community-hub.

## Schemas

### Salon (`models.salon`)
- **SalonSessionRow** — sessions with title, date, format, facilitator, notes, organ_tags
- **Participant** — per-session participants with roles and consent tracking
- **Segment** — transcript segments with speaker, text, timestamps, confidence
- **TaxonomyNodeRow** — hierarchical topic taxonomy (organ → children)

### Reading (`models.reading`)
- **Curriculum** — multi-week reading programs with theme and organ focus
- **ReadingSessionRow** — individual sessions within a curriculum
- **Entry** — reading materials with author, source type, difficulty, organ_tags
- **SessionEntry** — many-to-many link between sessions and entries
- **DiscussionQuestion** — questions per session (opening, deep_dive, closing)
- **Guide** — structured discussion guides per session

### Community (`models.community`)
- **Event** — community events
- **Contributor** — community members
- **Contribution** — contributor activity records

## Installation

```bash
pip install -e .
```

For development:
```bash
pip install -e ".[dev]"
```

## Seed Data

The `seed/` directory contains JSON files for bootstrapping a Neon database:

| File | Content |
|------|---------|
| `taxonomy.json` | 41 taxonomy nodes (7 organs + children) |
| `curricula.json` | 3 curricula with 24 sessions |
| `reading_lists.json` | 39 reading entries across difficulty levels |
| `sample_sessions.json` | 2 realistic salon transcripts |

Seed the database:
```bash
DATABASE_URL=postgresql://... python scripts/seed_all.py
```

## Migrations

Uses Alembic for schema migrations:

```bash
DATABASE_URL=postgresql://... alembic upgrade head
```

## Usage

```python
from koinonia_db.models import SalonSessionRow, Curriculum, Base
from koinonia_db import get_engine, get_session_factory
```

## Dependencies

- SQLAlchemy 2.0+ (with asyncio support)
- psycopg 3.1+ (PostgreSQL driver)
- Alembic 1.13+ (migrations)

## Part of ORGAN-VI

This package is part of the [organvm-vi-koinonia](https://github.com/organvm-vi-koinonia) organ — the community and fellowship layer of the eight-organ system.
