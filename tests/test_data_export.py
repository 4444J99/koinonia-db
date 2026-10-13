"""Tests for koinonia_db.data_export — schema manifest generation."""
import json
from pathlib import Path

from koinonia_db.data_export import (
    ALL_MODELS,
    _count_seed_entries,
    build_manifest,
    export_schema_manifest,
    export_seed_manifest,
    main,
)

SEED_DIR = Path(__file__).parent.parent / "seed"


def test_all_models_registered():
    """Every declared model class appears in ALL_MODELS."""
    assert len(ALL_MODELS) == 16


def test_schema_manifest_has_models():
    """export_schema_manifest returns info for all models."""
    result = export_schema_manifest()
    assert result["model_count"] == 16
    names = [m["class_name"] for m in result["models"]]
    assert "SalonSessionRow" in names
    assert "Curriculum" in names
    assert "LearningPathRow" in names


def test_schema_manifest_column_info():
    """Each model has columns with expected keys."""
    result = export_schema_manifest()
    for model in result["models"]:
        assert model["column_count"] > 0
        for col in model["columns"]:
            assert "name" in col
            assert "type" in col
            assert "nullable" in col
            assert "primary_key" in col


def test_schema_manifest_schemas():
    """Schema names include our four DB schemas."""
    result = export_schema_manifest()
    schemas = result["schemas"]
    assert "salons" in schemas
    assert "reading" in schemas
    assert "community" in schemas
    assert "syllabus" in schemas


def test_count_seed_entries_various_structures():
    """_count_seed_entries counts top-level lists and list-valued dict entries."""
    # Top-level list
    assert _count_seed_entries(["a", "b", "c"]) == 3

    # Dict with single list
    assert _count_seed_entries({"items": [1, 2, 3]}) == 3

    # Dict with multiple list collections
    assert _count_seed_entries({"events": [1, 2, 3], "contributors": [1]}) == 4
    assert _count_seed_entries({"a": [1, 2, 3, 4, 5, 6], "b": [1, 2, 3, 4, 5, 6]}) == 12

    # Scalars do not contribute
    assert _count_seed_entries({"name": "test", "version": 1, "items": [1, 2]}) == 2

    # Empty lists contribute zero
    assert _count_seed_entries({"empty": [], "items": [1]}) == 1

    # Unsupported scalar-only structure returns zero
    assert _count_seed_entries({"name": "test", "version": 1}) == 0
    assert _count_seed_entries("string_data") == 0
    assert _count_seed_entries(123) == 0


def test_seed_manifest_with_real_seed():
    """Seed manifest correctly inventories the actual seed directory."""
    result = export_seed_manifest(SEED_DIR)
    assert result["total_seed_entries"] == 68
    assert result["seed_files"]["community.json"]["entries"] == 4
    assert result["seed_files"]["product_communities.json"]["entries"] == 12
    assert result["seed_files"]["curricula.json"]["entries"] == 3
    assert result["seed_files"]["reading_lists.json"]["entries"] == 39
    assert result["seed_files"]["sample_sessions.json"]["entries"] == 2
    assert result["seed_files"]["taxonomy.json"]["entries"] == 8


def test_seed_manifest_missing_dir(tmp_path):
    """Seed manifest handles a nonexistent directory gracefully."""
    result = export_seed_manifest(tmp_path / "nonexistent")
    assert result["total_seed_entries"] == 0
    assert result["seed_files"] == {}


def test_build_manifest_structure():
    """build_manifest returns all expected top-level keys."""
    result = build_manifest(SEED_DIR)
    assert "generated_at" in result
    assert "package_version" in result
    assert "model_count" in result
    assert "models" in result
    assert "model_details" in result
    assert "schemas" in result
    assert "seed_files" in result
    assert "total_seed_entries" in result
    assert isinstance(result["models"], list)
    assert isinstance(result["model_details"], list)


def test_main_writes_file(tmp_path):
    """main() writes schema-manifest.json to the output directory."""
    out = main(output_dir=tmp_path, seed_dir=SEED_DIR)
    assert out.exists()
    assert out.name == "schema-manifest.json"
    data = json.loads(out.read_text())
    assert data["model_count"] == 16
    assert data["total_seed_entries"] > 0
