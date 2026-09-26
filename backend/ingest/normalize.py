"""Normalización de vocabulario, nombres y variantes (MASTER_PROMPT §6.2).

Cualquier valor de músculo, equipamiento o zona corporal que no figure en ``specs/`` hace
fallar la ingesta con :class:`UnmappedValueError`.
"""

import re
import string
import unicodedata
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from typing import Final, cast, get_args

from ingest.domain import BodyPart, DemoSex, EquipmentCode, EquipmentGroup, MuscleCode, VariantKind
from ingest.source import RawExercise
from ingest.specs import IngestSpecs

MOJIBAKE_CHAR: Final = "в"
_BODY_PARTS: Final[frozenset[str]] = frozenset(get_args(BodyPart))
_SEX_SUFFIX: Final = re.compile(r"\s*\((male|female)\)\s*$")
_VERSION_SUFFIX: Final = re.compile(r"\s+v\.\s*(\d+)\s*$")
_POV_SUFFIX: Final = re.compile(r"\s*\((back|side) pov\)\s*$")
_CAMERA_LABELS_ES: Final = {"back": "vista trasera", "side": "vista lateral"}
_DEMO_LABELS_ES: Final = {"male": "demostración masculina", "female": "demostración femenina"}


class UnmappedValueError(ValueError):
    """Valor del dataset sin correspondencia en las tablas de normalización."""


class DisplayNameError(ValueError):
    """Nombre visible inválido tras aplicar correcciones (p. ej. mojibake residual)."""


@dataclass(frozen=True, slots=True)
class VariantSuffixes:
    base_name: str
    demo_sex: DemoSex | None
    version: int | None
    camera: str | None


@dataclass(frozen=True, slots=True)
class NormalizedExercise:
    """Registro con vocabulario canónico y variantes resueltas (aún sin enriquecer)."""

    id: str
    media_id: str
    name_en: str
    display_name_en: str
    slug: str
    body_part: BodyPart
    equipment_code: EquipmentCode
    equipment_group: EquipmentGroup
    target_muscle: MuscleCode
    primary_group_muscle: MuscleCode
    secondary_muscles: tuple[MuscleCode, ...]
    raw_target: str
    raw_equipment: str
    raw_body_part: str
    demo_sex: DemoSex | None
    version: int | None
    camera: str | None
    variant_group: str
    variant_kind: VariantKind | None
    variant_label_es: str | None
    thumb_path: str
    gif_path: str
    instructions: dict[str, str]
    instruction_steps: dict[str, tuple[str, ...]]


def fix_display_name(exercise_id: str, name: str, specs: IngestSpecs) -> str:
    """Aplica ``name-fixes.yaml`` (override por id o sustituciones) sin tocar ``name_en``."""
    fixes = specs.name_fixes
    if exercise_id in fixes.by_id:
        fixed = fixes.by_id[exercise_id]
    else:
        padded = f" {name.strip()} "
        for wrong, right in fixes.replace_substrings.items():
            padded = padded.replace(wrong, right)
        fixed = padded
    fixed = " ".join(fixed.split())
    if MOJIBAKE_CHAR in fixed:
        msg = f"El nombre de {exercise_id} conserva mojibake tras corregirlo: {fixed!r}"
        raise DisplayNameError(msg)
    return fixed


def split_variant_suffixes(name: str) -> VariantSuffixes:
    """Retira sufijos ``(male)``/``(female)``, ``v. N`` y ``(back|side pov)`` en cualquier orden."""
    base = name
    demo_sex: DemoSex | None = None
    version: int | None = None
    camera: str | None = None
    changed = True
    while changed:
        changed = False
        if (match := _SEX_SUFFIX.search(base)) and demo_sex is None:
            demo_sex = "male" if match.group(1) == "male" else "female"
            base, changed = base[: match.start()], True
        if (match := _VERSION_SUFFIX.search(base)) and version is None:
            version = int(match.group(1))
            base, changed = base[: match.start()], True
        if (match := _POV_SUFFIX.search(base)) and camera is None:
            camera = match.group(1)
            base, changed = base[: match.start()], True
    return VariantSuffixes(base.strip(), demo_sex, version, camera)


def slugify(text: str) -> str:
    """Slug ASCII en minúsculas con guiones (``45°`` ⇒ ``45``)."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    return slug or "exercise"


def _map_muscle(value: str, field: str, exercise_id: str, specs: IngestSpecs) -> MuscleCode:
    key = value.strip().lower()
    try:
        return specs.muscles.map[key]
    except KeyError:
        msg = f"Músculo sin mapear en {field} de {exercise_id}: {value!r}"
        raise UnmappedValueError(msg) from None


def map_equipment(
    value: str, exercise_id: str, specs: IngestSpecs
) -> tuple[EquipmentCode, EquipmentGroup]:
    """Código y grupo de equipamiento según ``equipment-normalization.yaml``."""
    try:
        entry = specs.equipment.map[value.strip().lower()]
    except KeyError:
        msg = f"Equipamiento sin mapear en {exercise_id}: {value!r}"
        raise UnmappedValueError(msg) from None
    return entry.code, entry.group


def _override_equipment(
    code: EquipmentCode, specs: IngestSpecs
) -> tuple[EquipmentCode, EquipmentGroup]:
    """Grupo de un código de equipamiento forzado por ``enrichment-overrides.yaml``."""
    for entry in specs.equipment.map.values():
        if entry.code == code:
            return code, entry.group
    msg = f"equipment_code {code!r} de un override no existe en equipment-normalization.yaml"
    raise UnmappedValueError(msg)


def map_body_part(value: str, exercise_id: str) -> BodyPart:
    """``body_part`` del dataset con espacios ⇒ ``snake_case`` del contrato."""
    candidate = value.strip().lower().replace(" ", "_")
    if candidate in _BODY_PARTS:
        return cast("BodyPart", candidate)
    msg = f"Zona corporal sin mapear en {exercise_id}: {value!r}"
    raise UnmappedValueError(msg)


def _dedupe[T](values: Iterable[T]) -> tuple[T, ...]:
    return tuple(dict.fromkeys(values))


def normalize_record(raw: RawExercise, specs: IngestSpecs) -> NormalizedExercise:
    """Normaliza un registro; la agrupación de variantes se resuelve en :func:`normalize_all`."""
    equipment_code, equipment_group = map_equipment(raw.equipment, raw.id, specs)
    override = specs.overrides.by_id.get(raw.id)
    if override is not None and override.equipment_code is not None:
        equipment_code, equipment_group = _override_equipment(override.equipment_code, specs)
    display = fix_display_name(raw.id, raw.name, specs)
    suffixes = split_variant_suffixes(display)
    return NormalizedExercise(
        id=raw.id,
        media_id=raw.media_id,
        name_en=raw.name,
        display_name_en=suffixes.base_name,
        slug=f"{slugify(suffixes.base_name)}-{raw.id}",
        body_part=map_body_part(raw.body_part, raw.id),
        equipment_code=equipment_code,
        equipment_group=equipment_group,
        target_muscle=_map_muscle(raw.target, "target", raw.id, specs),
        primary_group_muscle=_map_muscle(raw.muscle_group, "muscle_group", raw.id, specs),
        secondary_muscles=_dedupe(
            _map_muscle(value, "secondary_muscles", raw.id, specs)
            for value in raw.secondary_muscles
        ),
        raw_target=raw.target.strip().lower(),
        raw_equipment=raw.equipment.strip().lower(),
        raw_body_part=raw.body_part.strip().lower(),
        demo_sex=suffixes.demo_sex,
        version=suffixes.version,
        camera=suffixes.camera,
        variant_group="",
        variant_kind=None,
        variant_label_es=None,
        thumb_path=f"thumbs/{_basename(raw.image)}",
        gif_path=f"gifs/{_basename(raw.gif_url)}",
        instructions=dict(raw.instructions),
        instruction_steps=dict(raw.instruction_steps),
    )


def _basename(path: str) -> str:
    return path.rsplit("/", 1)[-1]


def _duplicate_letter(position: int) -> str:
    return string.ascii_uppercase[position % len(string.ascii_uppercase)]


def _variant_kind_and_label(
    exercise: NormalizedExercise, duplicate_position: int
) -> tuple[VariantKind | None, str | None]:
    if exercise.version is not None:
        return "version", f"variante {exercise.version}"
    if exercise.camera is not None:
        return "camera_angle", _CAMERA_LABELS_ES[exercise.camera]
    if duplicate_position > 0:
        return "duplicate", f"(variante {_duplicate_letter(duplicate_position)})"
    if exercise.demo_sex is not None:
        return "demonstrator", _DEMO_LABELS_ES[exercise.demo_sex]
    return None, None


def assign_variant_groups(
    exercises: Sequence[NormalizedExercise],
) -> tuple[NormalizedExercise, ...]:
    """Agrupa por slug del nombre base (sin sufijos) y asigna ``variant_group``, tipo y etiqueta.

    Dentro de un grupo, los registros con idéntico conjunto de sufijos son duplicados: el de
    menor id es la base y el resto reciben ``duplicate`` con «(variante B)», «(variante C)»…
    """
    by_group: dict[str, list[NormalizedExercise]] = defaultdict(list)
    for exercise in exercises:
        # El slug agrupa también nombres que solo difieren en guiones o paréntesis
        # («close-grip press» / «close grip press»).
        by_group[slugify(exercise.display_name_en)].append(exercise)
    result: list[NormalizedExercise] = []
    for group, members in by_group.items():
        seen_signatures: dict[tuple[object, ...], int] = defaultdict(int)
        for exercise in sorted(members, key=lambda item: item.id):
            signature = (exercise.demo_sex, exercise.version, exercise.camera)
            position = seen_signatures[signature]
            seen_signatures[signature] += 1
            kind, label = _variant_kind_and_label(exercise, position)
            result.append(
                replace(exercise, variant_group=group, variant_kind=kind, variant_label_es=label)
            )
    return tuple(sorted(result, key=lambda item: item.id))


def normalize_all(
    records: Sequence[RawExercise], specs: IngestSpecs
) -> tuple[NormalizedExercise, ...]:
    """Normaliza todos los registros; cualquier valor sin mapear aborta la ingesta."""
    normalized = [normalize_record(record, specs) for record in records]
    slugs = [exercise.slug for exercise in normalized]
    if len(set(slugs)) != len(slugs):
        msg = "Se han generado slugs duplicados"
        raise DisplayNameError(msg)
    return assign_variant_groups(normalized)


def unmapped_values(records: Sequence[RawExercise], specs: IngestSpecs) -> dict[str, set[str]]:
    """Valores de vocabulario del dataset sin mapear (vacío si la cobertura es del 100 %)."""
    missing: dict[str, set[str]] = defaultdict(set)
    for record in records:
        for field, value in (("target", record.target), ("muscle_group", record.muscle_group)):
            if value.strip().lower() not in specs.muscles.map:
                missing[field].add(value)
        for value in record.secondary_muscles:
            if value.strip().lower() not in specs.muscles.map:
                missing["secondary_muscles"].add(value)
        if record.equipment.strip().lower() not in specs.equipment.map:
            missing["equipment"].add(record.equipment)
        if record.body_part.strip().lower().replace(" ", "_") not in _BODY_PARTS:
            missing["body_part"].add(record.body_part)
    return dict(missing)
