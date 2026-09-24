"""Fixtures de los tests de ingesta.

- ``fixtures/exercises.json``: 60 registros reales completos del dataset @ 7455efae (datos MIT,
  ver ``fixtures/LICENSE``) con todas las peculiaridades de ``docs/dataset-analysis.md``.
- ``fixtures/dataset-index.json``: proyección de los 1.324 registros sin instrucciones, para
  comprobar vocabularios, enriquecimiento, staples y nombres ES sin red. El test ``slow``
  verifica que coincide con el dataset real.
- Los medios de los repos de prueba son imágenes sintéticas generadas con Pillow: los medios
  de Gym visual nunca se versionan (ADR 0004).
"""

import json
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from ingest.catalog import Catalog, build_catalog
from ingest.source import RawExercise, load_dataset
from ingest.specs import IngestSpecs, load_specs

FIXTURES = Path(__file__).parent / "fixtures"
REPO_ROOT = Path(__file__).resolve().parents[3]
DATASET_COMMIT = "7455efae41b330c265e7cd4b78dfa848e7ce5ebd"
POSTGRES_IMAGE = "postgres:16-alpine"


def fixture_data() -> list[dict[str, Any]]:
    data: list[dict[str, Any]] = json.loads((FIXTURES / "exercises.json").read_text("utf-8"))
    return data


def index_records() -> tuple[RawExercise, ...]:
    """Los 1.324 registros (sin instrucciones: no las necesita el enriquecimiento)."""
    items = json.loads((FIXTURES / "dataset-index.json").read_text("utf-8"))
    return tuple(
        RawExercise.model_validate({**item, "instructions": {}, "instruction_steps": {}})
        for item in items
    )


@pytest.fixture(scope="session")
def specs() -> IngestSpecs:
    return load_specs()


@pytest.fixture(scope="session")
def fixture_dataset_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Directorio con la estructura ``data/`` del dataset y los 60 registros de fixture."""
    return dataset_dir(tmp_path_factory.mktemp("fixture-dataset"))


@pytest.fixture(scope="session")
def fixture_records(fixture_dataset_dir: Path) -> tuple[RawExercise, ...]:
    return load_dataset(fixture_dataset_dir)


def dataset_dir(root: Path) -> Path:
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(FIXTURES / "exercises.json", data_dir / "exercises.json")
    shutil.copyfile(FIXTURES / "exercises.schema.json", data_dir / "exercises.schema.json")
    return root


@pytest.fixture(scope="session")
def all_records() -> tuple[RawExercise, ...]:
    return index_records()


@pytest.fixture(scope="session")
def full_catalog(all_records: tuple[RawExercise, ...], specs: IngestSpecs) -> Catalog:
    return build_catalog(all_records, specs)


@pytest.fixture(scope="session")
def fixture_catalog(fixture_records: tuple[RawExercise, ...], specs: IngestSpecs) -> Catalog:
    return build_catalog(fixture_records, specs, full_dataset=False)


def write_media(path: Path, kind: str, size: tuple[int, int] = (180, 180)) -> None:
    """Imagen sintética (no es un medio de Gym visual)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", size, color=(len(path.name) * 7 % 255, 40, 90))
    if kind == "gif":
        image.convert("P").save(path, format="GIF")
    else:
        image.save(path, format="JPEG")


def git(*args: str, cwd: Path) -> str:
    git_bin = shutil.which("git")
    assert git_bin is not None
    completed = subprocess.run(  # noqa: S603 (argumentos fijos de test)
        [git_bin, *args], cwd=cwd, capture_output=True, text=True, check=True
    )
    return completed.stdout.strip()


def make_dataset_repo(
    root: Path,
    records: list[dict[str, Any]] | None = None,
    *,
    sizes: dict[str, tuple[int, int]] | None = None,
    skip_media: frozenset[str] = frozenset(),
) -> tuple[Path, str]:
    """Repo git local con la estructura del dataset; devuelve (ruta, sha del commit)."""
    records = fixture_data() if records is None else records
    root.mkdir(parents=True, exist_ok=True)
    (root / "data").mkdir(exist_ok=True)
    (root / "data" / "exercises.json").write_text(json.dumps(records), encoding="utf-8")
    shutil.copyfile(FIXTURES / "exercises.schema.json", root / "data" / "exercises.schema.json")
    shutil.copyfile(FIXTURES / "LICENSE", root / "LICENSE")
    (root / "NOTICE.md").write_text("© Gym visual — https://gymvisual.com/\n", encoding="utf-8")
    for record in records:
        for kind, key in (("thumb", "image"), ("gif", "gif_url")):
            if record[key] in skip_media:
                continue
            write_media(root / record[key], kind, (sizes or {}).get(record[key], (180, 180)))
    git("init", "--quiet", cwd=root)
    git("config", "user.email", "tests@forja.invalid", cwd=root)
    git("config", "user.name", "Forja tests", cwd=root)
    git("config", "uploadpack.allowAnySHA1InWant", "true", cwd=root)
    git("add", "-A", cwd=root)
    git("commit", "--quiet", "-m", "dataset", cwd=root)
    return root, git("rev-parse", "HEAD", cwd=root)


@pytest.fixture
def dataset_repo(tmp_path: Path) -> tuple[Path, str]:
    return make_dataset_repo(tmp_path / "repo")


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    """PostgreSQL 16 desechable (testcontainers) para los tests de ``load``."""
    from testcontainers.community.postgres import PostgresContainer  # noqa: PLC0415

    with PostgresContainer(POSTGRES_IMAGE, driver="asyncpg") as container:
        yield container.get_connection_url()
