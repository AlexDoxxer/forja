"""Obtención del dataset y de los medios de Gym visual (MASTER_PROMPT §2.1, §6.1, ADR 0004).

Los medios se copian **byte a byte**: nunca se reescalan, recodifican ni convierten. Pillow
solo se usa en modo lectura para comprobar formato y dimensiones (180x180).
"""

import hashlib
import json
import shutil
import subprocess
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, Literal

from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ingest.source import DATA_FILE, SCHEMA_FILE, RawExercise, load_dataset

MEDIA_SIZE: Final = (180, 180)
MANIFEST_FILE: Final = "manifest.json"
SOURCE_DIR: Final = "source"
LICENSE_FILES: Final = ("LICENSE", "NOTICE.md")
_CHUNK: Final = 1 << 20
_FORMATS: Final = {"thumb": "JPEG", "gif": "GIF"}

MediaKind = Literal["thumb", "gif"]


class FetchError(RuntimeError):
    """Fallo al obtener o verificar el dataset o sus medios."""


class ManifestFile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    exercise_id: str = Field(pattern=r"^[0-9]{4}$")
    kind: MediaKind
    path: str
    bytes: int = Field(ge=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    width: int
    height: int


class Manifest(BaseModel):
    """``$MEDIA_ROOT/manifest.json``: sin marcas de tiempo, para que sea reproducible."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    repo: str
    commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    files: tuple[ManifestFile, ...]

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n"

    def sha256(self) -> str:
        """Hash del ``manifest.json`` canónico (``ingest_run.checksums_sha256``)."""
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()

    def by_path(self) -> dict[str, ManifestFile]:
        return {item.path: item for item in self.files}


@dataclass(frozen=True, slots=True)
class MediaDiff:
    added: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()
    changed: tuple[str, ...] = ()

    @property
    def empty(self) -> bool:
        return not (self.added or self.removed or self.changed)


@dataclass(frozen=True, slots=True)
class VerifyResult:
    verified: int
    errors: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass(frozen=True, slots=True)
class FetchResult:
    status: Literal["unchanged", "updated", "dry_run"]
    commit: str
    exercises: int
    diff: MediaDiff
    verified: int


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def media_dimensions(path: Path, kind: MediaKind) -> tuple[int, int]:
    """Ancho y alto leídos con Pillow en solo lectura; el formato debe ser el esperado."""
    try:
        with Image.open(path) as image:
            if image.format != _FORMATS[kind]:
                msg = f"{path.name}: formato {image.format}, se esperaba {_FORMATS[kind]}"
                raise FetchError(msg)
            return image.size
    except (OSError, UnidentifiedImageError) as exc:
        msg = f"{path.name}: no es una imagen válida ({exc})"
        raise FetchError(msg) from exc


def _describe(source: Path, exercise_id: str, kind: MediaKind, target: str) -> ManifestFile:
    if not source.is_file():
        msg = f"Falta el medio {source.name} del ejercicio {exercise_id}"
        raise FetchError(msg)
    width, height = media_dimensions(source, kind)
    if (width, height) != MEDIA_SIZE:
        msg = f"{source.name}: {width}x{height}, se exige 180x180 (licencia de Gym visual)"
        raise FetchError(msg)
    return ManifestFile(
        exercise_id=exercise_id,
        kind=kind,
        path=target,
        bytes=source.stat().st_size,
        sha256=sha256_file(source),
        width=width,
        height=height,
    )


def _media_sources(record: RawExercise) -> tuple[tuple[MediaKind, str, str], ...]:
    thumb_name = record.image.rsplit("/", 1)[-1]
    gif_name = record.gif_url.rsplit("/", 1)[-1]
    return (
        ("thumb", record.image, f"thumbs/{thumb_name}"),
        ("gif", record.gif_url, f"gifs/{gif_name}"),
    )


def build_manifest(
    checkout: Path, records: Sequence[RawExercise], *, repo: str, commit: str
) -> Manifest:
    """Describe los medios de ``checkout`` (verifica existencia, formato y 180x180)."""
    files = [
        _describe(checkout / source, record.id, kind, target)
        for record in records
        for kind, source, target in _media_sources(record)
    ]
    return Manifest(repo=repo, commit=commit, files=tuple(sorted(files, key=lambda f: f.path)))


def read_manifest(media_root: Path) -> Manifest | None:
    path = media_root / MANIFEST_FILE
    if not path.is_file():
        return None
    try:
        return Manifest.model_validate_json(path.read_text(encoding="utf-8"))
    except ValidationError as exc:
        msg = f"{path} no es un manifest válido: {exc}"
        raise FetchError(msg) from exc


def diff_manifests(old: Manifest | None, new: Manifest) -> MediaDiff:
    """Altas, bajas y cambios de medios entre dos manifests."""
    before = old.by_path() if old else {}
    after = new.by_path()
    return MediaDiff(
        added=tuple(sorted(set(after) - set(before))),
        removed=tuple(sorted(set(before) - set(after))),
        changed=tuple(
            sorted(p for p in set(after) & set(before) if after[p].sha256 != before[p].sha256)
        ),
    )


def verify_media(media_root: Path, manifest: Manifest) -> VerifyResult:
    """Comprueba que cada medio del manifest existe, coincide en SHA-256 y mide 180x180."""
    errors: list[str] = []
    verified = 0
    for item in manifest.files:
        path = media_root / item.path
        if not path.is_file():
            errors.append(f"falta {item.path}")
            continue
        if sha256_file(path) != item.sha256:
            errors.append(f"SHA-256 distinto en {item.path}")
            continue
        try:
            size = media_dimensions(path, item.kind)
        except FetchError as exc:
            errors.append(str(exc))
            continue
        if size != MEDIA_SIZE:
            errors.append(f"{item.path}: {size[0]}x{size[1]} ≠ 180x180")
            continue
        verified += 1
    return VerifyResult(verified=verified, errors=tuple(errors))


def _git(*args: str, cwd: Path) -> str:
    git = shutil.which("git")
    if git is None:
        msg = "No se encuentra el ejecutable git"
        raise FetchError(msg)
    # Lista de argumentos fija (sin shell); repo y commit se validan antes de llegar aquí.
    completed = subprocess.run(  # noqa: S603
        [git, *args], cwd=cwd, capture_output=True, text=True, check=False
    )
    if completed.returncode != 0:
        msg = f"git {' '.join(args)} falló: {completed.stderr.strip()}"
        raise FetchError(msg)
    return completed.stdout.strip()


def clone_at_commit(repo: str, commit: str, dest: Path) -> None:
    """Clon superficial del commit exacto (``git fetch --depth 1 <sha>``)."""
    if len(commit) != 40 or any(char not in "0123456789abcdef" for char in commit):  # noqa: PLR2004
        msg = f"DATASET_COMMIT debe ser un SHA-1 completo en minúsculas: {commit!r}"
        raise FetchError(msg)
    dest.mkdir(parents=True, exist_ok=True)
    _git("init", "--quiet", cwd=dest)
    _git("remote", "add", "origin", repo, cwd=dest)
    _git("fetch", "--quiet", "--depth", "1", "origin", commit, cwd=dest)
    _git("checkout", "--quiet", "FETCH_HEAD", cwd=dest)
    head = _git("rev-parse", "HEAD", cwd=dest)
    if head != commit:
        msg = f"El checkout apunta a {head}, se esperaba {commit}"
        raise FetchError(msg)


def _copy_verified(source: Path, target: Path, sha256: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    if sha256_file(target) != sha256:
        msg = f"La copia de {source.name} no coincide byte a byte con el origen"
        raise FetchError(msg)


def install(
    checkout: Path, records: Sequence[RawExercise], manifest: Manifest, media_root: Path
) -> None:
    """Copia medios, licencias y datos al volumen y escribe ``manifest.json`` al final."""
    by_path = manifest.by_path()
    for record in records:
        for _kind, source, target in _media_sources(record):
            _copy_verified(checkout / source, media_root / target, by_path[target].sha256)
    licenses = media_root / "LICENSES"
    licenses.mkdir(parents=True, exist_ok=True)
    for name in LICENSE_FILES:
        if not (checkout / name).is_file():
            msg = f"El dataset no incluye {name}"
            raise FetchError(msg)
        shutil.copyfile(checkout / name, licenses / name)
    source_dir = media_root / SOURCE_DIR
    for relative in (DATA_FILE, SCHEMA_FILE):
        (source_dir / relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(checkout / relative, source_dir / relative)
    (media_root / MANIFEST_FILE).write_text(manifest.to_json(), encoding="utf-8")


def is_current(media_root: Path, commit: str) -> bool:
    """El volumen ya contiene ese commit con todos los medios verificados."""
    manifest = read_manifest(media_root)
    if manifest is None or manifest.commit != commit:
        return False
    if not all((media_root / SOURCE_DIR / name).is_file() for name in (DATA_FILE, SCHEMA_FILE)):
        return False
    if not all((media_root / "LICENSES" / name).is_file() for name in LICENSE_FILES):
        return False
    return verify_media(media_root, manifest).ok


def fetch(
    repo: str,
    commit: str,
    media_root: Path,
    *,
    dry_run: bool = False,
    workdir: Path | None = None,
) -> FetchResult:
    """``forja-ingest fetch``: idempotente; con ``dry_run`` solo calcula el diff."""
    existing = read_manifest(media_root)
    if existing is not None and is_current(media_root, commit):
        records = load_dataset(media_root / SOURCE_DIR)
        return FetchResult("unchanged", commit, len(records), MediaDiff(), len(existing.files))
    with tempfile.TemporaryDirectory(prefix="forja-dataset-", dir=workdir) as tmp:
        checkout = Path(tmp) / "dataset"
        clone_at_commit(repo, commit, checkout)
        records = load_dataset(checkout)
        manifest = build_manifest(checkout, records, repo=repo, commit=commit)
        diff = diff_manifests(existing, manifest)
        if dry_run:
            return FetchResult("dry_run", commit, len(records), diff, 0)
        install(checkout, records, manifest, media_root)
    result = verify_media(media_root, manifest)
    if not result.ok:
        raise FetchError("; ".join(result.errors[:20]))
    return FetchResult("updated", commit, len(records), diff, result.verified)
