"""Tests for transaction ownership contract in syllabus generation service.

Verifies that `generate_learning_path` stages/flushes rows without committing,
leaving commit/rollback control strictly to the caller.
"""

from __future__ import annotations

import json
import sqlite3
from unittest.mock import patch

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.types import ARRAY

from koinonia_db.models import (
    Base,
    LearnerProfileRow,
    LearningModuleRow,
    LearningPathRow,
    TaxonomyNodeRow,
)
from koinonia_db.syllabus_service import generate_learning_path

# Register list adapter for sqlite3 so ARRAY mapped columns function in SQLite in-memory
sqlite3.register_adapter(list, json.dumps)


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(type_, compiler, **kw):
    return "JSON"


@pytest.fixture
async def ephemeral_db():
    """Create an isolated, ephemeral in-memory SQLite database engine with all schemas/tables."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.execute(text("ATTACH DATABASE ':memory:' AS salons"))
        await conn.execute(text("ATTACH DATABASE ':memory:' AS reading"))
        await conn.execute(text("ATTACH DATABASE ':memory:' AS community"))
        await conn.execute(text("ATTACH DATABASE ':memory:' AS syllabus"))
        await conn.run_sync(Base.metadata.create_all)

    # Seed sample taxonomy nodes required for path generation
    session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        root = TaxonomyNodeRow(slug="i-theoria", label="Theoria")
        session.add(root)
        child = TaxonomyNodeRow(slug="theoria-foundations", label="Foundations", parent=root)
        session.add(child)
        await session.commit()

    yield engine
    await engine.dispose()


@pytest.fixture
async def async_session(ephemeral_db):
    """Provide an AsyncSession bound to the ephemeral test database."""
    session_factory = sessionmaker(ephemeral_db, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.mark.asyncio
async def test_generation_does_not_call_commit(async_session: AsyncSession):
    """Verify generate_learning_path flushes changes but never calls session.commit()."""
    with patch.object(async_session, "commit", wraps=async_session.commit) as mock_commit:
        result = await generate_learning_path(
            async_session,
            organs=["I"],
            level="beginner",
            name="No Commit Test Learner",
        )
        assert mock_commit.call_count == 0
        assert result["path_id"] is not None


@pytest.mark.asyncio
async def test_caller_rollback_removes_generated_graph_and_unrelated_staged_changes(
    async_session: AsyncSession, ephemeral_db
):
    """Verify caller rollback removes generated learner/path/modules AND unrelated staged changes."""
    # Stage unrelated caller object before calling generation service
    unrelated_learner = LearnerProfileRow(
        name="Unrelated Staged Learner",
        organs_of_interest=["II"],
        level="intermediate",
    )
    async_session.add(unrelated_learner)

    # Call syllabus generation service
    response = await generate_learning_path(
        async_session,
        organs=["I"],
        level="beginner",
        name="Rollback Test Learner",
    )
    path_id = response["path_id"]

    # Caller decides to roll back transaction
    await async_session.rollback()

    # Query using a fresh session to verify database state
    fresh_session_factory = sessionmaker(ephemeral_db, class_=AsyncSession, expire_on_commit=False)
    async with fresh_session_factory() as check_session:
        # Check unrelated staged learner was rolled back
        unrelated_check = (
            await check_session.execute(
                select(LearnerProfileRow).where(
                    LearnerProfileRow.name == "Unrelated Staged Learner"
                )
            )
        ).scalars().first()
        assert unrelated_check is None

        # Check generated learner was rolled back
        generated_learner = (
            await check_session.execute(
                select(LearnerProfileRow).where(
                    LearnerProfileRow.name == "Rollback Test Learner"
                )
            )
        ).scalars().first()
        assert generated_learner is None

        # Check generated path was rolled back
        generated_path = (
            await check_session.execute(
                select(LearningPathRow).where(LearningPathRow.path_id == path_id)
            )
        ).scalars().first()
        assert generated_path is None

        # Check generated modules were rolled back
        generated_modules = (
            await check_session.execute(
                select(LearningModuleRow).where(
                    LearningModuleRow.module_id == "theoria-foundations-beg"
                )
            )
        ).scalars().all()
        assert len(generated_modules) == 0


@pytest.mark.asyncio
async def test_explicit_caller_commit_persists_complete_graph(
    async_session: AsyncSession, ephemeral_db
):
    """Verify explicit caller commit persists complete graph of generated data and unrelated changes."""
    # Stage unrelated caller object
    unrelated_learner = LearnerProfileRow(
        name="Unrelated Staged Learner Commit",
        organs_of_interest=["III"],
        level="advanced",
    )
    async_session.add(unrelated_learner)

    # Call syllabus generation service
    response = await generate_learning_path(
        async_session,
        organs=["I"],
        level="beginner",
        name="Commit Test Learner",
    )
    path_id = response["path_id"]

    # Explicit caller commit
    await async_session.commit()

    # Query using a fresh session to verify persistence
    fresh_session_factory = sessionmaker(ephemeral_db, class_=AsyncSession, expire_on_commit=False)
    async with fresh_session_factory() as check_session:
        unrelated_check = (
            await check_session.execute(
                select(LearnerProfileRow).where(
                    LearnerProfileRow.name == "Unrelated Staged Learner Commit"
                )
            )
        ).scalars().first()
        assert unrelated_check is not None

        generated_learner = (
            await check_session.execute(
                select(LearnerProfileRow).where(
                    LearnerProfileRow.name == "Commit Test Learner"
                )
            )
        ).scalars().first()
        assert generated_learner is not None

        generated_path = (
            await check_session.execute(
                select(LearningPathRow).where(LearningPathRow.path_id == path_id)
            )
        ).scalars().first()
        assert generated_path is not None
        assert generated_path.learner_id == generated_learner.id

        generated_modules = (
            await check_session.execute(
                select(LearningModuleRow).where(
                    LearningModuleRow.path_id == generated_path.id
                )
            )
        ).scalars().all()
        assert len(generated_modules) > 0


@pytest.mark.asyncio
async def test_successful_response_remains_compatible(async_session: AsyncSession):
    """Verify generate_learning_path returns compatible structure and expected keys/values."""
    response = await generate_learning_path(
        async_session,
        organs=["I"],
        level="beginner",
        name="Response Compatibility Learner",
    )

    expected_keys = {"path_id", "title", "organs", "level", "total_hours", "modules"}
    assert set(response.keys()) == expected_keys
    assert isinstance(response["path_id"], str)
    assert response["title"] == "Learning Path: I"
    assert response["organs"] == ["I"]
    assert response["level"] == "beginner"
    assert isinstance(response["total_hours"], float)
    assert isinstance(response["modules"], list)


@pytest.mark.asyncio
async def test_failure_cannot_independently_commit_partial_state(
    async_session: AsyncSession, ephemeral_db
):
    """Verify that an error raised during processing leaves uncommitted changes rollbackable."""
    unrelated_learner = LearnerProfileRow(
        name="Pre-Failure Learner",
        organs_of_interest=["IV"],
        level="beginner",
    )
    async_session.add(unrelated_learner)

    # Perform generation
    await generate_learning_path(
        async_session,
        organs=["I"],
        level="beginner",
        name="Failed Operation Learner",
    )

    # Simulate subsequent error in caller operation before commit
    try:
        raise RuntimeError("Simulated caller workflow failure")
    except RuntimeError:
        await async_session.rollback()

    # Query in fresh session to confirm no state was persisted
    fresh_session_factory = sessionmaker(ephemeral_db, class_=AsyncSession, expire_on_commit=False)
    async with fresh_session_factory() as check_session:
        failed_check = (
            await check_session.execute(
                select(LearnerProfileRow).where(
                    LearnerProfileRow.name == "Failed Operation Learner"
                )
            )
        ).scalars().first()
        assert failed_check is None

        pre_failed_check = (
            await check_session.execute(
                select(LearnerProfileRow).where(
                    LearnerProfileRow.name == "Pre-Failure Learner"
                )
            )
        ).scalars().first()
        assert pre_failed_check is None
