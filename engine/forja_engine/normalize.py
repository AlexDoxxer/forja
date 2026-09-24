"""Paso 1 (§7.2): normalizar y validar la entrada, reglas de seguridad y semilla derivada."""

import hashlib
import json
import random
from enum import StrEnum

from forja_engine.models import (
    MAX_SEED,
    EquipmentCode,
    EquipmentPreset,
    EquipmentSelection,
    Experience,
    GeneratorInput,
    MovementPattern,
    MuscleCode,
    PlanWarning,
    PlanWarningCode,
    Weekday,
)
from forja_engine.tables import Tables

HIGH_FREQUENCY_DAYS = 6
RECOVERY_DAYS = 7


def _enum_sorted[E: StrEnum](values: tuple[E, ...], enum: type[E]) -> tuple[E, ...]:
    order = {member: index for index, member in enumerate(enum)}
    return tuple(sorted(values, key=order.__getitem__))


def resolve_equipment(selection: EquipmentSelection, tables: Tables) -> tuple[EquipmentCode, ...]:
    """Lista de equipamiento efectiva: preset resuelto + lo siempre disponible, ordenada."""
    preset = tables.equipment_normalization.presets[selection.preset]
    if selection.preset is EquipmentPreset.CUSTOM:
        items = set(selection.items)
    elif preset == "*":
        items = set(EquipmentCode)
    else:
        items = set(preset)
    items.update(tables.engine_rules.always_available_equipment)
    return _enum_sorted(tuple(items), EquipmentCode)


def canonical_json(data: object) -> str:
    """JSON canónico (claves ordenadas, sin espacios) usado para semillas y hashes."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def derive_seed(*parts: object) -> int:
    """Semilla estable en [0, 2^53-1] a partir del SHA-256 de las partes."""
    digest = hashlib.sha256(canonical_json([str(p) for p in parts]).encode("utf-8")).hexdigest()
    return int(digest[:16], 16) % (MAX_SEED + 1)


def rng_for(seed: int, *scope: object) -> random.Random:
    """PRNG local sembrado por (seed, semana, día, slot…); nunca el ``random`` global."""
    return random.Random(derive_seed(seed, *scope))  # noqa: S311 - no criptográfico


def normalize_input(raw: GeneratorInput, tables: Tables) -> GeneratorInput:
    """Entrada normalizada: defectos resueltos, listas ordenadas y semilla no nula."""
    defaults = tables.engine_rules.goal_defaults[raw.goal]
    normalized = raw.model_copy(
        update={
            "equipment": EquipmentSelection(
                preset=raw.equipment.preset, items=resolve_equipment(raw.equipment, tables)
            ),
            "avoid_muscles": _enum_sorted(raw.avoid_muscles, MuscleCode),
            "avoid_patterns": _enum_sorted(raw.avoid_patterns, MovementPattern),
            "preferred_days": _enum_sorted(raw.preferred_days, Weekday),
            "include_warmup": defaults.include_warmup
            if raw.include_warmup is None
            else raw.include_warmup,
            "include_cooldown": defaults.include_cooldown
            if raw.include_cooldown is None
            else raw.include_cooldown,
            "include_cardio_finisher": defaults.include_cardio_finisher
            if raw.include_cardio_finisher is None
            else raw.include_cardio_finisher,
            "favorite_exercise_ids": tuple(sorted(raw.favorite_exercise_ids)),
            "excluded_exercise_ids": tuple(sorted(raw.excluded_exercise_ids)),
        }
    )
    if normalized.seed is None:
        payload = normalized.model_dump(mode="json", exclude={"seed"})
        normalized = normalized.model_copy(update={"seed": derive_seed(canonical_json(payload))})
    return GeneratorInput.model_validate(normalized.model_dump())


def safety_warnings(inp: GeneratorInput) -> list[PlanWarning]:
    """Reglas de seguridad de §7.2 paso 1 (se mantiene la frecuencia pero se avisa)."""
    warnings: list[PlanWarning] = []
    if inp.experience is Experience.BEGINNER and inp.days_per_week >= HIGH_FREQUENCY_DAYS:
        warnings.append(
            PlanWarning(
                code=PlanWarningCode.BEGINNER_HIGH_FREQUENCY,
                message_es=(
                    f"Entrenar {inp.days_per_week} días por semana siendo principiante es mucho: "
                    "hemos repartido el volumen para que cada sesión sea más ligera. Si notas "
                    "fatiga acumulada, prueba con 3 o 4 días."
                ),
            )
        )
    if inp.days_per_week == RECOVERY_DAYS:
        warnings.append(
            PlanWarning(
                code=PlanWarningCode.RECOVERY_DAY_ENFORCED,
                message_es=(
                    "Con 7 días por semana, uno de ellos es obligatoriamente de recuperación "
                    "activa (cardio suave y movilidad): el descanso también construye progreso."
                ),
            )
        )
    return warnings
