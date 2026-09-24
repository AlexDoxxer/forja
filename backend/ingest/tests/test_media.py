"""``fetch`` (§6.1): clon del commit exacto, copia byte a byte, manifest e idempotencia.

Los repos de prueba son locales y sus medios son imágenes sintéticas de Pillow.
"""

import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image

from ingest.media import (
    MANIFEST_FILE,
    SOURCE_DIR,
    FetchError,
    Manifest,
    build_manifest,
    clone_at_commit,
    diff_manifests,
    fetch,
    media_dimensions,
    read_manifest,
    verify_media,
)
from ingest.source import SourceError, load_dataset
from ingest.tests.conftest import fixture_data, git, make_dataset_repo, write_media


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_fetch_copies_media_byte_for_byte(dataset_repo: tuple[Path, str], tmp_path: Path) -> None:
    repo, commit = dataset_repo
    media_root = tmp_path / "media"
    result = fetch(repo.as_uri(), commit, media_root)
    assert result.status == "updated"
    assert result.exercises == 60
    assert result.verified == 120
    assert len(result.diff.added) == 120
    manifest = read_manifest(media_root)
    assert manifest is not None
    assert manifest.commit == commit
    for item in manifest.files:
        assert (item.width, item.height) == (180, 180)
        folder = "images" if item.kind == "thumb" else "videos"
        source = repo / folder / Path(item.path).name
        assert _sha(media_root / item.path) == _sha(source) == item.sha256
        assert (media_root / item.path).stat().st_size == item.bytes
    assert (media_root / "LICENSES" / "LICENSE").is_file()
    assert (media_root / "LICENSES" / "NOTICE.md").is_file()
    assert len(load_dataset(media_root / SOURCE_DIR)) == 60
    assert (
        manifest.sha256() == hashlib.sha256((media_root / MANIFEST_FILE).read_bytes()).hexdigest()
    )


def test_second_fetch_is_a_no_op(dataset_repo: tuple[Path, str], tmp_path: Path) -> None:
    repo, commit = dataset_repo
    media_root = tmp_path / "media"
    fetch(repo.as_uri(), commit, media_root)
    before = {p: p.stat().st_mtime_ns for p in media_root.rglob("*") if p.is_file()}
    result = fetch("file:///nonexistent-repo", commit, media_root)
    assert result.status == "unchanged"
    assert result.diff.empty
    after = {p: p.stat().st_mtime_ns for p in media_root.rglob("*") if p.is_file()}
    assert before == after


def test_dry_run_reports_diff_without_writing(
    dataset_repo: tuple[Path, str], tmp_path: Path
) -> None:
    repo, commit = dataset_repo
    media_root = tmp_path / "media"
    result = fetch(repo.as_uri(), commit, media_root, dry_run=True)
    assert result.status == "dry_run"
    assert len(result.diff.added) == 120
    assert not media_root.exists()


def test_new_commit_is_diffed_and_installed(tmp_path: Path) -> None:
    records = fixture_data()
    repo, first = make_dataset_repo(tmp_path / "repo", records[:10])
    media_root = tmp_path / "media"
    fetch(repo.as_uri(), first, media_root)
    (repo / "data" / "exercises.json").write_text(json.dumps(records[:9]), encoding="utf-8")
    image = repo / records[2]["image"]
    Image.new("RGB", (180, 180), (1, 2, 3)).save(image, format="JPEG")
    git("add", "-A", cwd=repo)
    git("commit", "--quiet", "-m", "update", cwd=repo)
    second = git("rev-parse", "HEAD", cwd=repo)
    preview = fetch(repo.as_uri(), second, media_root, dry_run=True)
    assert len(preview.diff.removed) == 2
    assert records[2]["image"].replace("images/", "thumbs/") in preview.diff.changed
    result = fetch(repo.as_uri(), second, media_root)
    assert result.status == "updated"
    manifest = read_manifest(media_root)
    assert manifest is not None
    assert manifest.commit == second
    assert len(manifest.files) == 18


def test_wrong_dimensions_are_rejected(tmp_path: Path) -> None:
    records = fixture_data()[:3]
    repo, commit = make_dataset_repo(
        tmp_path / "repo", records, sizes={records[1]["gif_url"]: (360, 360)}
    )
    with pytest.raises(FetchError, match="180x180"):
        fetch(repo.as_uri(), commit, tmp_path / "media")


def test_missing_media_is_rejected(tmp_path: Path) -> None:
    records = fixture_data()[:3]
    repo, commit = make_dataset_repo(
        tmp_path / "repo", records, skip_media=frozenset({records[2]["image"]})
    )
    with pytest.raises(FetchError, match="Falta el medio"):
        fetch(repo.as_uri(), commit, tmp_path / "media")


def test_invalid_schema_is_rejected(tmp_path: Path) -> None:
    records = fixture_data()[:2]
    records[0]["body_part"] = "tail"
    repo, commit = make_dataset_repo(tmp_path / "repo", records)
    with pytest.raises(SourceError, match=r"exercises\.schema\.json"):
        fetch(repo.as_uri(), commit, tmp_path / "media")


def test_missing_license_is_rejected(tmp_path: Path) -> None:
    repo, _ = make_dataset_repo(tmp_path / "repo", fixture_data()[:2])
    (repo / "NOTICE.md").unlink()
    git("add", "-A", cwd=repo)
    git("commit", "--quiet", "-m", "sin aviso", cwd=repo)
    commit = git("rev-parse", "HEAD", cwd=repo)
    with pytest.raises(FetchError, match=r"NOTICE\.md"):
        fetch(repo.as_uri(), commit, tmp_path / "media")


def test_clone_validates_commit_and_reports_git_errors(tmp_path: Path) -> None:
    with pytest.raises(FetchError, match="SHA-1"):
        clone_at_commit("file:///x", "HEAD", tmp_path / "a")
    with pytest.raises(FetchError, match="git fetch"):
        clone_at_commit(tmp_path.as_uri() + "/missing", "0" * 40, tmp_path / "b")


def test_clone_without_git_binary(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("ingest.media.shutil.which", lambda _name: None)
    with pytest.raises(FetchError, match="git"):
        clone_at_commit("file:///x", "0" * 40, tmp_path)


def test_verify_detects_tampering(dataset_repo: tuple[Path, str], tmp_path: Path) -> None:
    repo, commit = dataset_repo
    media_root = tmp_path / "media"
    fetch(repo.as_uri(), commit, media_root)
    manifest = read_manifest(media_root)
    assert manifest is not None
    first, second, third, fourth = (media_root / item.path for item in manifest.files[:4])
    first.unlink()
    second.write_bytes(second.read_bytes() + b"x")
    write_media(third, "gif" if third.suffix == ".gif" else "thumb", (100, 100))
    kinds = {item.path: item.kind for item in manifest.files}
    wrong_format = fourth
    rebuilt = manifest.model_copy(
        update={
            "files": tuple(
                item.model_copy(update={"sha256": _sha(media_root / item.path)})
                if media_root / item.path in {third, wrong_format}
                else item
                for item in manifest.files
            )
        }
    )
    fourth_kind = kinds[str(fourth.relative_to(media_root))]
    other_kind = "gif" if fourth_kind == "thumb" else "thumb"
    write_media(fourth, other_kind)
    rebuilt = rebuilt.model_copy(
        update={
            "files": tuple(
                item.model_copy(update={"sha256": _sha(fourth)})
                if media_root / item.path == fourth
                else item
                for item in rebuilt.files
            )
        }
    )
    result = verify_media(media_root, rebuilt)
    assert not result.ok
    assert result.verified == 116
    joined = " ".join(result.errors)
    assert "falta" in joined
    assert "SHA-256" in joined
    assert "180x180" in joined
    assert "formato" in joined
    assert fetch(repo.as_uri(), commit, media_root).status == "updated"


def test_media_dimensions_rejects_non_images(tmp_path: Path) -> None:
    path = tmp_path / "fake.jpg"
    path.write_bytes(b"not an image")
    with pytest.raises(FetchError, match="no es una imagen"):
        media_dimensions(path, "thumb")


def test_invalid_manifest_is_reported(tmp_path: Path) -> None:
    (tmp_path / MANIFEST_FILE).write_text('{"files": 3}', encoding="utf-8")
    with pytest.raises(FetchError, match="manifest"):
        read_manifest(tmp_path)


def test_manifest_diff(dataset_repo: tuple[Path, str]) -> None:
    repo, commit = dataset_repo
    records = load_dataset(repo)
    manifest = build_manifest(repo, records, repo="r", commit=commit)
    assert diff_manifests(manifest, manifest).empty
    smaller = Manifest(repo="r", commit=commit, files=manifest.files[2:])
    assert len(diff_manifests(smaller, manifest).added) == 2
    assert len(diff_manifests(manifest, smaller).removed) == 2


@pytest.mark.parametrize("missing", ["source/data/exercises.json", "LICENSES/NOTICE.md"])
def test_incomplete_volume_is_refetched(
    dataset_repo: tuple[Path, str], tmp_path: Path, missing: str
) -> None:
    repo, commit = dataset_repo
    media_root = tmp_path / "media"
    fetch(repo.as_uri(), commit, media_root)
    (media_root / missing).unlink()
    assert fetch(repo.as_uri(), commit, media_root).status == "updated"
    assert (media_root / missing).is_file()
