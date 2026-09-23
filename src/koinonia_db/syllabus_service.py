"""Shared syllabus generation service for ORGAN-VI.

Extracts learning-path generation logic so both community-hub and
adaptive-personal-syllabus can use the same code path.
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from koinonia_db.constants import ORGAN_MAP, DIFFICULTY_ORDER
from koinonia_db.models.salon import TaxonomyNodeRow
from koinonia_db.models.reading import Entry
from koinonia_db.models.syllabus import LearnerProfileRow, LearningPathRow, LearningModuleRow


async def generate_learning_path(
    session: AsyncSession,
    organs: list[str],
    level: str,
    name: str,
) -> dict:
    """Generate a personalized learning path from DB data and persist it.

    Args:
        session: Async SQLAlchemy session (caller manages commit/rollback).
        organs: List of organ codes (e.g. ["I", "III"]).
        level: Difficulty level — "beginner", "intermediate", or "advanced".
        name: Learner display name.

    Returns:
        Dict with path_id, title, organs, level, total_hours, and modules list.
    """
    # Load taxonomy roots
    roots = (await session.execute(
        select(TaxonomyNodeRow).where(TaxonomyNodeRow.parent_id.is_(None))
    )).scalars().all()

    taxonomy = {}
    for root in roots:
        children = (await session.execute(
            select(TaxonomyNodeRow).where(TaxonomyNodeRow.parent_id == root.id)
        )).scalars().all()
        taxonomy[root.slug] = {
            "label": root.label,
            "children": [{"slug": c.slug, "label": c.label} for c in children],
        }

    # Load readings
    entries = (await session.execute(select(Entry))).scalars().all()
    readings = [
        {"title": e.title, "organ_tags": e.organ_tags or [], "difficulty": e.difficulty}
        for e in entries
    ]

    # Build modules filtered by level
    if level == "beginner":
        allowed = {"beginner", "intermediate"}
    elif level == "intermediate":
        allowed = {"intermediate", "advanced"}
    else:
        allowed = {"advanced"}

    modules = []
    for organ_code in organs:
        organ_slug = ORGAN_MAP.get(organ_code, organ_code.lower())
        organ_node = taxonomy.get(organ_slug)
        if not organ_node:
            continue

        organ_readings = [
            r for r in readings
            if any(
                tag.startswith(organ_slug.split("-")[0] + "-") or tag == organ_slug
                for tag in r.get("organ_tags", [])
            )
        ]
        filtered = [r for r in organ_readings if r.get("difficulty", "intermediate") in allowed]

        for child in organ_node.get("children", []):
            child_readings = [r["title"] for r in filtered][:3]
            if not child_readings:
                child_readings = [f"See {organ_node['label']} documentation"]

            modules.append({
                "module_id": f"{child['slug']}-{level[:3]}",
                "title": child["label"],
                "organ": organ_slug,
                "difficulty": level,
                "readings": child_readings,
                "questions": [
                    f"What is the core idea behind {child['label']}?",
                    f"How does {child['label']} connect to {organ_node['label']}?",
                    f"What would you build or explore using {child['label']}?",
                ],
                "estimated_hours": 2.0 if level != "advanced" else 3.0,
            })

    modules.sort(key=lambda m: DIFFICULTY_ORDER.get(m["difficulty"], 1))
    total_hours = sum(m["estimated_hours"] for m in modules)

    # Persist learner, path, and modules
    path_id = uuid4().hex[:8]
    learner = LearnerProfileRow(
        name=name or "anonymous",
        organs_of_interest=organs,
        level=level,
    )
    session.add(learner)
    await session.flush()

    path_row = LearningPathRow(
        path_id=path_id,
        title=f"Learning Path: {', '.join(organs)}",
        learner_id=learner.id,
        total_hours=total_hours,
    )
    session.add(path_row)
    await session.flush()

    for i, mod in enumerate(modules):
        session.add(LearningModuleRow(
            path_id=path_row.id,
            module_id=mod["module_id"],
            title=mod["title"],
            organ=mod["organ"],
            difficulty=mod["difficulty"],
            readings=mod["readings"],
            questions=mod["questions"],
            estimated_hours=mod["estimated_hours"],
            seq=i,
        ))

    await session.flush()

    return {
        "path_id": path_id,
        "title": path_row.title,
        "organs": organs,
        "level": level,
        "total_hours": total_hours,
        "modules": modules,
    }
