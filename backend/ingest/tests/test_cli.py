"""CLI ``forja-ingest``: los seis subcomandos con ``--dry-run`` y sus errores."""

import json
import shutil
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from ingest.cli import app, main
from ingest.media import MANIFEST_FILE
from ingest.tests.conftest import FIXTURES, REPO_ROOT

runner = CliRunner()


@pytest.fixture
def fetched(dataset_repo: tuple[Path, str], tmp_path: Path) -> Path:
    repo, commit = dataset_repo
    media_root = tmp_path / "media"
    result = runner.invoke(
        app, ["fetch", "--media-root", str(media_root), "--repo", repo.as_uri(), "--commit", commit]
    )
    assert result.exit_code == 0, result.output
    assert "fetch updated" in result.output
    return media_root


@pytest.fixture
def subset_specs(tmp_path: Path) -> Path:
    """specs/ sin referencias a ids ausentes de la fixture (para el modo dataset completo)."""
    target = tmp_path / "specs"
    shutil.copytree(REPO_ROOT / "specs", target)
    ids = {item["id"] for item in json.loads((FIXTURES / "exercises.json").read_text("utf-8"))}
    names = json.loads((target / "overrides" / "names_es.json").read_text("utf-8"))
    (target / "overrides" / "names_es.json").write_text(
        json.dumps({key: value for key, value in names.items() if key in ids}), encoding="utf-8"
    )
    (target / "overrides" / "staples.yaml").write_text(
        "version: 1\nstaples:\n  squat: ['0043', '0042']\n", encoding="utf-8"
    )
    overrides_path = target / "overrides" / "enrichment-overrides.yaml"
    overrides = yaml.safe_load(overrides_path.read_text("utf-8"))
    overrides["other_justified"] = {
        key: value for key, value in overrides["other_justified"].items() if key in ids
    }
    overrides["by_id"] = {key: value for key, value in overrides["by_id"].items() if key in ids}
    overrides_path.write_text(yaml.safe_dump(overrides, allow_unicode=True), encoding="utf-8")
    fixes_path = target / "overrides" / "name-fixes.yaml"
    fixes = yaml.safe_load(fixes_path.read_text("utf-8"))
    fixes["by_id"] = {key: value for key, value in fixes["by_id"].items() if key in ids}
    fixes_path.write_text(yaml.safe_dump(fixes, allow_unicode=True), encoding="utf-8")
    (target / "overrides" / "names-es-exceptions.yaml").write_text("version: 1\n", "utf-8")
    return target


def test_help_lists_the_six_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("fetch", "enrich", "load", "report", "verify", "export-cards"):
        assert command in result.output


def test_main_entry_point(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["forja-ingest", "--help"])
    with pytest.raises(SystemExit) as exit_info:
        main()
    assert exit_info.value.code == 0


def test_fetch_dry_run_and_idempotency(dataset_repo: tuple[Path, str], tmp_path: Path) -> None:
    repo, commit = dataset_repo
    media_root = tmp_path / "media"
    args = ["fetch", "--media-root", str(media_root), "--repo", repo.as_uri(), "--commit", commit]
    dry = runner.invoke(app, [*args, "--dry-run"])
    assert dry.exit_code == 0, dry.output
    assert "alta: gifs/" in dry.output
    assert not media_root.exists()
    assert runner.invoke(app, args).exit_code == 0
    again = runner.invoke(app, args)
    assert "fetch unchanged" in again.output


def test_fetch_error_exit_code(tmp_path: Path) -> None:
    result = runner.invoke(app, ["fetch", "--media-root", str(tmp_path), "--commit", "not-a-sha"])
    assert result.exit_code == 1
    assert "SHA-1" in result.output


def test_enrich_verify_report_and_export(fetched: Path, subset_specs: Path, tmp_path: Path) -> None:
    common = ["--media-root", str(fetched), "--specs-dir", str(subset_specs)]
    enrich = runner.invoke(app, ["enrich", *common, "--dry-run"])
    assert enrich.exit_code == 1  # la fixture no cubre la matriz de staples
    assert "enrich (dry-run): 60 ejercicios" in enrich.output
    assert "celda vertical_pull x bodyweight" in enrich.output

    verify = runner.invoke(app, ["verify", *common])
    assert "120/120 medios verificados" in verify.output
    assert verify.exit_code == 1

    report_path = tmp_path / "report.md"
    dry = runner.invoke(app, ["report", *common, "--output", str(report_path), "--dry-run"])
    assert "cambiaría" in dry.output
    assert not report_path.exists()
    written = runner.invoke(app, ["report", *common, "--output", str(report_path)])
    assert written.exit_code == 0, written.output
    assert report_path.read_text("utf-8").startswith("# Informe de enriquecimiento")
    same = runner.invoke(app, ["report", *common, "--output", str(report_path)])
    assert "ya está al día" in same.output

    cards_path = tmp_path / "cards.json"
    dry_cards = runner.invoke(
        app, ["export-cards", *common, "--output", str(cards_path), "--dry-run"]
    )
    assert "60 tarjetas" in dry_cards.output
    assert not cards_path.exists()
    exported = runner.invoke(app, ["export-cards", *common, "--output", str(cards_path)])
    assert exported.exit_code == 0, exported.output
    assert len(json.loads(cards_path.read_text("utf-8"))) == 60


def test_enrich_passes_on_full_dataset(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset"
    (dataset / "data").mkdir(parents=True)
    index = json.loads((FIXTURES / "dataset-index.json").read_text("utf-8"))
    langs = ("en", "es", "it", "tr", "ru", "zh", "hi", "pl", "ko", "fr")
    instructions = dict.fromkeys(langs, "texto")
    steps = {lang: ["paso"] for lang in instructions}
    full = [
        {
            **item,
            "instructions": instructions,
            "instruction_steps": steps,
            "created_at": "2026-03-18T12:31:32+00:00",
        }
        for item in index
    ]
    (dataset / "data" / "exercises.json").write_text(json.dumps(full), encoding="utf-8")
    shutil.copyfile(FIXTURES / "exercises.schema.json", dataset / "data" / "exercises.schema.json")
    result = runner.invoke(app, ["enrich", "--dataset-dir", str(dataset)])
    assert result.exit_code == 0, result.output
    assert "enrich: 1324 ejercicios" in result.output


def test_commands_fail_cleanly_without_data(tmp_path: Path) -> None:
    for command in (["enrich"], ["report", "--output", str(tmp_path / "r.md")], ["verify"]):
        result = runner.invoke(app, [*command, "--media-root", str(tmp_path)])
        assert result.exit_code == 1
        assert "ERROR" in result.output
    export = runner.invoke(
        app, ["export-cards", "--media-root", str(tmp_path), "--output", str(tmp_path / "c.json")]
    )
    assert export.exit_code == 1


def test_load_requires_asyncpg_url_and_manifest(tmp_path: Path) -> None:
    bad_url = runner.invoke(
        app, ["load", "--media-root", str(tmp_path), "--database-url", "postgresql://x/y"]
    )
    assert bad_url.exit_code == 1
    assert "postgresql+asyncpg" in bad_url.output
    no_manifest = runner.invoke(
        app,
        ["load", "--media-root", str(tmp_path), "--database-url", "postgresql+asyncpg://x/y"],
    )
    assert no_manifest.exit_code == 1
    assert "manifest.json" in no_manifest.output


def test_load_rejects_tampered_media(fetched: Path) -> None:
    manifest = json.loads((fetched / MANIFEST_FILE).read_text("utf-8"))
    (fetched / manifest["files"][0]["path"]).write_bytes(b"x")
    result = runner.invoke(
        app,
        ["load", "--media-root", str(fetched), "--database-url", "postgresql+asyncpg://x/y"],
    )
    assert result.exit_code == 1
    assert "SHA-256" in result.output


@pytest.mark.integration
def test_load_command_against_postgres(
    fetched: Path, subset_specs: Path, postgres_url: str
) -> None:
    common = [
        "--media-root",
        str(fetched),
        "--specs-dir",
        str(subset_specs),
        "--database-url",
        postgres_url,
    ]
    dry = runner.invoke(app, ["load", *common, "--create-schema", "--dry-run"])
    assert dry.exit_code == 0, dry.output
    assert "load (dry-run)" in dry.output
    first = runner.invoke(app, ["load", *common])
    assert first.exit_code == 0, first.output
    assert "120 medios verificados" in first.output
    unreachable = runner.invoke(
        app,
        [
            "load",
            "--media-root",
            str(fetched),
            "--specs-dir",
            str(subset_specs),
            "--database-url",
            "postgresql+asyncpg://nobody:nothing@127.0.0.1:1/none",
        ],
    )
    assert unreachable.exit_code == 1
    assert "ERROR" in unreachable.output
