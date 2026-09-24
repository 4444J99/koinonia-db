# koinonia-db

Shared database models, migrations, and seed data for all ORGAN-VI Koinonia repositories.

[![CI](https://github.com/organvm-vi-koinonia/koinonia-db/actions/workflows/ci.yml/badge.svg)](https://github.com/organvm-vi-koinonia/koinonia-db/actions/workflows/ci.yml)

## Overview

koinonia-db is the single source of truth for ORGAN-VI's PostgreSQL schema. It provides SQLAlchemy ORM models consumed by `salon-archive`, `reading-group-curriculum`, `adaptive-personal-syllabus`, and `community-hub`.

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

## Installation & Deployment

### User & Dependency Installation

In downstream services or local Python environments, install from git repository release tag or local editable checkout:

```bash
# Standard local editable install
pip install -e .

# Install with development & test dependencies
pip install -e ".[dev]"

# Direct installation from git release tag
pip install git+https://github.com/organvm-vi-koinonia/koinonia-db.0.5.0@v0.5.0
```

### Packaging & Distribution

Release outputs (wheels and source distributions) are built and attached to GitHub Release tags via the CI release pipeline (`.github/workflows/release.yml`). To build artifacts locally:

```bash
pip install build
python -m build
```

The compiled wheel and source archive will be output to `dist/`.

## Health Check & Verification

To verify database connectivity and model configuration:

### 1. Environment Verification

Ensure `DATABASE_URL` or `POSTGRES_URL` is set in your environment:

```bash
export DATABASE_URL="postgresql+psycopg://user:password@localhost:5432/koinonia"
```

### 2. Runtime Health Check Snippet

You can run a quick health check via python to verify database connection and engine initialization:

```python
import asyncio
from koinonia_db.config import require_database_url
from koinonia_db.engine import get_engine, get_session_factory
from sqlalchemy import text

async def health_check():
    db_url = require_database_url()
    print(f"Connecting to database endpoint...")
    engine = get_engine(db_url)
    session_factory = get_session_factory(engine)
    async with session_factory() as session:
        result = await session.execute(text("SELECT 1"))
        print(f"Health check status: OK (result={result.scalar()})")

if __name__ == "__main__":
    asyncio.run(health_check())
```

### 3. Migration Health Check

Verify database schema migration status:

```bash
DATABASE_URL=postgresql://user:password@localhost:5432/koinonia alembic current
```

Upgrade to latest schema:

```bash
DATABASE_URL=postgresql://user:password@localhost:5432/koinonia alembic upgrade head
```

## Seed Data

The `seed/` directory contains JSON files for bootstrapping a database:

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

## Usage

```python
from koinonia_db.models import SalonSessionRow, Curriculum, Base
from koinonia_db import get_engine, get_session_factory
```

## CLI Export Utility

`koinonia-db` includes a command-line utility for exporting schema data:

```bash
koinonia-data-export --help
```

## Dependencies

- SQLAlchemy 2.0+ (with asyncio support)
- psycopg 3.1+ (PostgreSQL driver)
- Alembic 1.13+ (migrations)

## Part of ORGAN-VI

This package is part of the [organvm-vi-koinonia](https://github.com/organvm-vi-koinonia) organ — the community and fellowship layer of the eight-organ system.
