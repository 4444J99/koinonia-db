"""Generate static data artifacts from koinonia-db models and seed data.

Produces data/schema-manifest.json — a JSON manifest of all ORM models,
their columns, and an inventory of seed data files with entry counts.
No database connection required; reads models via SQLAlchemy introspection
and seed files from disk.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from koinonia_db.models import (
    Contribution,
    Contributor,
    Curriculum,
    DiscussionQuestion,
    Entry,
    Event,
    Guide,
    LearnerProfileRow,
    LearningModuleRow,
    LearningPathRow,
    Participant,
    ReadingSessionRow,
    SalonSessionRow,
    Segment,
    SessionEntry,
    TaxonomyNodeRow,
)

PACKAGE_VERSION = "0.5.0"

# All model classes in declaration order
ALL_MODELS = [
    SalonSessionRow,
    Participant,
    Segment,
    TaxonomyNodeRow,
    Curriculum,
    ReadingSessionRow,
    Entry,
    SessionEntry,
    DiscussionQuestion,
    Guide,
    Event,
    Contributor,
    Contribution,
    LearnerProfileRow,
    LearningPathRow,
    LearningModuleRow,
]

SEED_DIR = Path(__file__).parent.parent.parent / "seed"


def _model_info(model_cls: type) -> dict[str, Any]:
    """Extract table name, schema, and column info from a SQLAlchemy model."""
    table = model_cls.__table__
    columns = []
    for col in table.columns:
        columns.append({
            "name": col.name,
            "type": str(col.type),
            "nullable": col.nullable,
            "primary_key": col.primary_key,
        })
    return {
        "class_name": model_cls.__name__,
        "table_name": table.name,
        "schema": table.schema,
        "column_count": len(columns),
        "columns": columns,
    }


def export_schema_manifest() -> dict[str, Any]:
    """Build a schema manifest from all registered ORM models."""
    models = [_model_info(m) for m in ALL_MODELS]
    return {
        "models": models,
        "model_count": len(models),
        "schemas": sorted({m["schema"] for m in models if m["schema"]}),
    }


def _count_seed_entries(data: Any) -> int:
    """Count top-level entries in a seed JSON structure."""
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        return sum(len(v) for v in data.values() if isinstance(v, list))
    return 0


def export_seed_manifest(seed_dir: Path | None = None) -> dict[str, Any]:
    """Inventory seed JSON files with entry counts."""
    seed_dir = seed_dir or SEED_DIR
    seed_files: dict[str, dict[str, Any]] = {}
    total_entries = 0

    if seed_dir.is_dir():
        for path in sorted(seed_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text())
                count = _count_seed_entries(data)
            except (json.JSONDecodeError, OSError):
                count = 0
            seed_files[path.name] = {"entries": count}
            total_entries += count

    return {
        "seed_dir": str(seed_dir),
        "seed_files": seed_files,
        "total_seed_entries": total_entries,
    }


def build_manifest(seed_dir: Path | None = None) -> dict[str, Any]:
    """Build the complete schema-manifest.json content."""
    schema = export_schema_manifest()
    seed = export_seed_manifest(seed_dir)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "package_version": PACKAGE_VERSION,
        "model_count": schema["model_count"],
        "models": [m["class_name"] for m in schema["models"]],
        "model_details": schema["models"],
        "schemas": schema["schemas"],
        "seed_files": seed["seed_files"],
        "total_seed_entries": seed["total_seed_entries"],
    }


def main(output_dir: Path | None = None, seed_dir: Path | None = None) -> Path:
    """Generate data/schema-manifest.json and return the output path."""
    output_dir = output_dir or Path(__file__).parent.parent.parent / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(seed_dir)
    out_path = output_dir / "schema-manifest.json"
    out_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return out_path


if __name__ == "__main__":
    path = main()
    print(f"Written: {path}")
