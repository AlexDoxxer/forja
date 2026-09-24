"""CLI ``forja-ingest`` (MASTER_PROMPT §6): ``fetch``, ``enrich``, ``load``, ``report``,
``verify`` y ``export-cards``. Todos son idempotentes y aceptan ``--dry-run``."""

import asyncio
from collections import Counter
from pathlib import Path
from typing import Annotated, Final

import typer

from ingest.catalog import Catalog, build_catalog, write_cards
from ingest.enrich import EnrichmentError
from ingest.media import (
    SOURCE_DIR,
    FetchError,
    fetch,
    read_manifest,
    verify_media,
)
from ingest.names import NamesError
from ingest.normalize import DisplayNameError, UnmappedValueError
from ingest.report import quality_problems, render_report
from ingest.source import SourceError, load_dataset
from ingest.specs import SpecError, load_specs

DEFAULT_REPO: Final = "https://github.com/hasaneyldrm/exercises-dataset"
DEFAULT_COMMIT: Final = "7455efae41b330c265e7cd4b78dfa848e7ce5ebd"
DEFAULT_MEDIA_ROOT: Final = Path("/var/lib/forja/media")
DEFAULT_REPORT: Final = Path(__file__).resolve().parents[2] / "docs" / "enrichment-report.md"
_EXPECTED_ERRORS: Final = (
    SpecError,
    SourceError,
    FetchError,
    UnmappedValueError,
    DisplayNameError,
    EnrichmentError,
    NamesError,
)

app = typer.Typer(
    name="forja-ingest",
    help="Ingesta del dataset hasaneyldrm/exercises-dataset en Forja.",
    no_args_is_help=True,
    add_completion=False,
)

MediaRoot = Annotated[
    Path, typer.Option("--media-root", envvar="MEDIA_ROOT", help="Volumen de medios.")
]
SpecsDir = Annotated[
    Path | None,
    typer.Option(
        "--specs-dir", envvar="FORJA_SPECS_DIR", help="Directorio specs/ (por defecto el del repo)."
    ),
]
DatasetDir = Annotated[
    Path | None,
    typer.Option(
        "--dataset-dir",
        help="Checkout del dataset (con data/exercises.json); por defecto $MEDIA_ROOT/source.",
    ),
]
DryRun = Annotated[bool, typer.Option("--dry-run", help="No escribe nada; muestra qué haría.")]


def _echo(message: str) -> None:
    typer.echo(message)


def _fail(message: str) -> typer.Exit:
    typer.echo(f"ERROR: {message}", err=True)
    return typer.Exit(code=1)


def _catalog(media_root: Path, dataset_dir: Path | None, specs_dir: Path | None) -> Catalog:
    specs = load_specs(specs_dir)
    records = load_dataset(dataset_dir or media_root / SOURCE_DIR)
    return build_catalog(records, specs)


@app.command("fetch")
def fetch_command(
    *,
    media_root: MediaRoot = DEFAULT_MEDIA_ROOT,
    repo: Annotated[str, typer.Option(envvar="DATASET_REPO")] = DEFAULT_REPO,
    commit: Annotated[str, typer.Option(envvar="DATASET_COMMIT")] = DEFAULT_COMMIT,
    dry_run: DryRun = False,
) -> None:
    """Clona el commit fijado, valida el esquema y copia los medios byte a byte."""
    try:
        result = fetch(repo, commit, media_root, dry_run=dry_run)
    except _EXPECTED_ERRORS as exc:
        raise _fail(str(exc)) from exc
    diff = result.diff
    _echo(
        f"fetch {result.status}: commit {result.commit}, {result.exercises} ejercicios, "
        f"medios +{len(diff.added)} -{len(diff.removed)} ~{len(diff.changed)}, "
        f"verificados {result.verified}"
    )
    if dry_run:
        for label, paths in (
            ("alta", diff.added),
            ("baja", diff.removed),
            ("cambio", diff.changed),
        ):
            for path in paths:
                _echo(f"  {label}: {path}")


@app.command("enrich")
def enrich_command(
    *,
    media_root: MediaRoot = DEFAULT_MEDIA_ROOT,
    dataset_dir: DatasetDir = None,
    specs_dir: SpecsDir = None,
    dry_run: DryRun = False,
) -> None:
    """Normaliza y enriquece el catálogo y comprueba sus requisitos (no escribe nada)."""
    try:
        catalog = _catalog(media_root, dataset_dir, specs_dir)
        problems = quality_problems(catalog, load_specs(specs_dir))
    except _EXPECTED_ERRORS as exc:
        raise _fail(str(exc)) from exc
    patterns = Counter(entry.enrichment.movement_pattern for entry in catalog.entries)
    _echo(f"enrich{' (dry-run)' if dry_run else ''}: {len(catalog.entries)} ejercicios")
    for pattern, count in sorted(patterns.items(), key=lambda item: (-item[1], item[0])):
        _echo(f"  {pattern}: {count}")
    if problems:
        raise _fail("; ".join(problems))


@app.command("report")
def report_command(
    *,
    media_root: MediaRoot = DEFAULT_MEDIA_ROOT,
    dataset_dir: DatasetDir = None,
    specs_dir: SpecsDir = None,
    output: Annotated[Path, typer.Option(help="Destino del informe.")] = DEFAULT_REPORT,
    dry_run: DryRun = False,
) -> None:
    """Genera ``docs/enrichment-report.md``; con ``--dry-run`` solo indica si cambiaría."""
    try:
        specs = load_specs(specs_dir)
        source = dataset_dir or media_root / SOURCE_DIR
        catalog = build_catalog(load_dataset(source), specs)
        manifest = read_manifest(media_root)
    except _EXPECTED_ERRORS as exc:
        raise _fail(str(exc)) from exc
    commit = manifest.commit if manifest else DEFAULT_COMMIT
    content = render_report(catalog, specs, commit)
    current = output.read_text(encoding="utf-8") if output.is_file() else None
    if current == content:
        _echo(f"report: {output} ya está al día")
        return
    if dry_run:
        _echo(f"report (dry-run): {output} cambiaría")
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    _echo(f"report: escrito {output}")


@app.command("verify")
def verify_command(
    *,
    media_root: MediaRoot = DEFAULT_MEDIA_ROOT,
    specs_dir: SpecsDir = None,
    dry_run: DryRun = False,
) -> None:
    """Verifica medios (SHA-256, 180x180), esquema del dataset y requisitos del catálogo."""
    del dry_run  # verify nunca escribe; se acepta por uniformidad con el resto de comandos
    try:
        manifest = read_manifest(media_root)
        if manifest is None:
            raise _fail(f"No existe {media_root}/manifest.json (ejecuta forja-ingest fetch)")
        result = verify_media(media_root, manifest)
        catalog = _catalog(media_root, None, specs_dir)
        problems = [*result.errors, *quality_problems(catalog, load_specs(specs_dir))]
    except _EXPECTED_ERRORS as exc:
        raise _fail(str(exc)) from exc
    _echo(
        f"verify: commit {manifest.commit}, {len(catalog.entries)} ejercicios, "
        f"{result.verified}/{len(manifest.files)} medios verificados"
    )
    if problems:
        raise _fail("; ".join(problems[:20]))


@app.command("load")
def load_command(
    *,
    media_root: MediaRoot = DEFAULT_MEDIA_ROOT,
    specs_dir: SpecsDir = None,
    database_url: Annotated[str, typer.Option(envvar="DATABASE_URL")] = "",
    create_schema: Annotated[
        bool, typer.Option("--create-schema", help="Crea extensiones y tablas si faltan.")
    ] = False,
    dry_run: DryRun = False,
) -> None:
    """Upsert transaccional del catálogo en PostgreSQL y registro en ``ingest_run``."""
    from sqlalchemy.exc import SQLAlchemyError  # noqa: PLC0415 (SQLAlchemy solo en load)

    from ingest.load import LoadError, load_catalog  # noqa: PLC0415

    if not database_url.startswith("postgresql+asyncpg://"):
        raise _fail("DATABASE_URL debe usar el esquema postgresql+asyncpg://")
    try:
        manifest = read_manifest(media_root)
        if manifest is None:
            raise _fail(f"No existe {media_root}/manifest.json (ejecuta forja-ingest fetch)")
        verified = verify_media(media_root, manifest)
        if not verified.ok:
            raise _fail("; ".join(verified.errors[:20]))
        specs = load_specs(specs_dir)
        catalog = build_catalog(load_dataset(media_root / SOURCE_DIR), specs)
        result = asyncio.run(
            load_catalog(
                database_url,
                catalog,
                manifest,
                specs,
                media_verified=verified.verified,
                dry_run=dry_run,
                create_schema=create_schema,
            )
        )
    except (*_EXPECTED_ERRORS, LoadError, SQLAlchemyError, OSError) as exc:
        raise _fail(str(exc)) from exc
    counts = result.counts
    _echo(
        f"load{' (dry-run)' if dry_run else ''}: run {result.run_id}, "
        f"{counts['exercises_total']} ejercicios (+{counts['added']} ~{counts['updated']} "
        f"={counts['unchanged']} deprecados {counts['deprecated']}), "
        f"{counts['media_verified']} medios verificados"
    )


@app.command("export-cards")
def export_cards_command(
    *,
    output: Annotated[Path, typer.Option(help="Fichero JSON de salida (lista de ExerciseCard).")],
    media_root: MediaRoot = DEFAULT_MEDIA_ROOT,
    dataset_dir: DatasetDir = None,
    specs_dir: SpecsDir = None,
    dry_run: DryRun = False,
) -> None:
    """Exporta el catálogo enriquecido como ``ExerciseCard[]`` para el motor de rutinas."""
    try:
        cards = _catalog(media_root, dataset_dir, specs_dir).cards()
    except _EXPECTED_ERRORS as exc:
        raise _fail(str(exc)) from exc
    if dry_run:
        _echo(f"export-cards (dry-run): {len(cards)} tarjetas para {output}")
        return
    write_cards(cards, output)
    _echo(f"export-cards: {len(cards)} tarjetas en {output}")


def main() -> None:
    app()
