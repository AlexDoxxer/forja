"""Carga y validación de las tablas YAML de ``specs/`` (MASTER_PROMPT §7, ADR 0005).

Cada fichero se valida con un modelo Pydantic estricto (``extra="forbid"``) y después se
comprueban las referencias cruzadas (plantillas de día, patrones, objetivos, niveles). Un
YAML inválido o una referencia rota lanzan :class:`TablesError` al cargar: fallo rápido.

``tables_hash`` es el SHA-256 del JSON canónico de todas las tablas cargadas; se guarda en
cada programa para poder reproducirlo o auditarlo.
"""

import hashlib
import json
import re
from functools import cache
from pathlib import Path
from typing import Any, Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, ValidationError, model_validator

from forja_engine.models import (
    Emphasis,
    EquipmentCode,
    EquipmentGroup,
    EquipmentPreset,
    ExerciseCard,
    ExerciseRole,
    Experience,
    Goal,
    LoadType,
    Mechanic,
    MovementPattern,
    MuscleCode,
    MuscleGroup,
    Sex,
    VolumeGroup,
)

DEFAULT_SPECS_DIR = Path(__file__).resolve().parents[2] / "specs"
"""Directorio ``specs/`` del repositorio (la imagen del backend lo copia con esta forma)."""

VOLUME_GROUP_VALUES: frozenset[str] = frozenset(g.value for g in VolumeGroup)

Range = tuple[int, int]
FloatRange = tuple[float, float]
MAX_TABLE_RIR = 5


class TablesError(ValueError):
    """Tabla YAML ausente, inválida o con referencias rotas."""


class Table(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)


class NameRule(Table):
    """Ejercicios que casan por palabra completa con ``display_name_en`` o por id."""

    name_en_any: tuple[str, ...] = Field(min_length=1)
    ids: tuple[str, ...] = ()

    def matches(self, card: ExerciseCard) -> bool:
        return (
            card.id in self.ids
            or _name_pattern(self.name_en_any).search(card.display_name_en) is not None
        )


@cache
def _name_pattern(terms: tuple[str, ...]) -> re.Pattern[str]:
    """Coincidencia por palabra completa (``ring`` no casa con «spring»), con plural en ``s``."""
    alternatives = "|".join(re.escape(term.lower()) for term in terms)
    return re.compile(rf"(?<![a-z0-9])(?:{alternatives})s?(?![a-z0-9])", re.IGNORECASE)


def _check_range(values: tuple[float, float], name: str) -> None:
    if values[0] > values[1]:
        msg = f"{name}: el mínimo {values[0]} supera el máximo {values[1]}"
        raise ValueError(msg)


# --------------------------------------------------------------------- split-templates
class SlotSpec(Table):
    pattern: MovementPattern
    role: ExerciseRole
    group: MuscleGroup
    priority: int = Field(ge=1, le=3)


class DayTemplate(Table):
    name_es: str
    slots: tuple[SlotSpec, ...] = Field(min_length=1)


class AppendBlock(Table):
    patterns: tuple[MovementPattern, ...] = Field(min_length=1)
    to: Literal["*"] | tuple[str, ...]


class EmphasisOverride(Table):
    min_days: int = Field(default=1, ge=1, le=7)
    replace_last_of: tuple[str, ...] = ()
    with_: str | None = Field(default=None, alias="with")
    append_block: AppendBlock | None = None

    @model_validator(mode="after")
    def _replace_needs_target(self) -> Self:
        if bool(self.replace_last_of) != (self.with_ is not None):
            msg = "replace_last_of y with van juntos"
            raise ValueError(msg)
        return self


class SplitTemplates(Table):
    version: int
    day_templates: dict[str, DayTemplate]
    splits: dict[int, dict[Experience, tuple[str, ...]]]
    emphasis_overrides: dict[Emphasis, EmphasisOverride]

    @model_validator(mode="after")
    def _check_references(self) -> Self:
        known = set(self.day_templates)
        for days in range(1, 8):
            by_level = self.splits.get(days)
            if by_level is None or set(by_level) != set(Experience):
                msg = f"splits[{days}] debe definir los tres niveles"
                raise ValueError(msg)
            for level, templates in by_level.items():
                if len(templates) != days:
                    msg = f"splits[{days}][{level}] debe tener {days} días"
                    raise ValueError(msg)
                _check_known(templates, known, f"splits[{days}][{level}]")
        if set(self.emphasis_overrides) != set(Emphasis):
            msg = "emphasis_overrides debe cubrir todos los énfasis"
            raise ValueError(msg)
        for emphasis, override in self.emphasis_overrides.items():
            names = list(override.replace_last_of)
            if override.with_ is not None:
                names.append(override.with_)
            if override.append_block is not None and override.append_block.to != "*":
                names.extend(override.append_block.to)
            _check_known(tuple(names), known, f"emphasis_overrides[{emphasis}]")
        return self


def _check_known(names: tuple[str, ...], known: set[str], where: str) -> None:
    unknown = sorted(set(names) - known)
    if unknown:
        msg = f"{where}: plantillas inexistentes {unknown}"
        raise ValueError(msg)


# ---------------------------------------------------------------------- volume-targets
class SetCredit(Table):
    target: float = Field(gt=0)
    relevant_secondary: float = Field(ge=0)


class VolumeTargets(Table):
    version: int
    groups: tuple[VolumeGroup, ...]
    targets: dict[Goal, dict[Experience, dict[str, FloatRange]]]
    set_credit: SetCredit
    secondary_credit_by_group: dict[VolumeGroup, float] = Field(default_factory=dict)
    max_effective_sets_per_group_per_session: float = Field(gt=0, le=10)
    maintenance_floor_ratio: float = Field(ge=0, le=1)
    emphasis_multipliers: dict[Emphasis, dict[str, float]]

    @model_validator(mode="after")
    def _check_coverage(self) -> Self:
        if set(self.groups) != set(VolumeGroup):
            msg = "groups debe coincidir con VolumeGroup"
            raise ValueError(msg)
        allowed = {"default"} | {g.value for g in VolumeGroup}
        for goal in Goal:
            by_level = self.targets.get(goal)
            if by_level is None or set(by_level) != set(Experience):
                msg = f"targets[{goal}] debe definir los tres niveles"
                raise ValueError(msg)
            for level, ranges in by_level.items():
                if "default" not in ranges or not set(ranges) <= allowed:
                    msg = f"targets[{goal}][{level}] necesita default y solo grupos válidos"
                    raise ValueError(msg)
                for key, values in ranges.items():
                    _check_range(values, f"targets[{goal}][{level}][{key}]")
        if set(self.emphasis_multipliers) != set(Emphasis):
            msg = "emphasis_multipliers debe cubrir todos los énfasis"
            raise ValueError(msg)
        for emphasis, multipliers in self.emphasis_multipliers.items():
            if not set(multipliers) <= allowed - {"default"} | {"*"}:
                msg = f"emphasis_multipliers[{emphasis}] con grupos inválidos"
                raise ValueError(msg)
        return self

    def target_range(self, goal: Goal, level: Experience, group: VolumeGroup) -> FloatRange:
        ranges = self.targets[goal][level]
        return ranges.get(group.value, ranges["default"])

    def secondary_credit(self, group: VolumeGroup) -> float:
        """Crédito de una serie compuesta al grupo secundario ``group`` (por grupo o el general)."""
        return self.secondary_credit_by_group.get(group, self.set_credit.relevant_secondary)

    def multiplier(self, emphasis: Emphasis, group: VolumeGroup) -> float:
        values = self.emphasis_multipliers[emphasis]
        return values.get(group.value, values.get("*", 1.0))


# ------------------------------------------------------------------------ prescription
class RoleRx(Table):
    sets: Range
    reps: Range
    rir: Range
    rest_s: Range
    tempo: str
    prefer_supersets: bool = False
    format: Literal["circuit"] | None = None

    @model_validator(mode="after")
    def _ranges(self) -> Self:
        for name in ("sets", "reps", "rir", "rest_s"):
            _check_range(getattr(self, name), name)
        return self


class CoreRx(Table):
    sets: Range
    reps: Range
    hold_s: Range
    rir: Range
    rest_s: Range


class WarmupRx(Table):
    sets: Range
    reps: Range
    hold_s: Range
    rest_s: Range


class CooldownRx(Table):
    sets: Range
    hold_s: Range
    per_side: bool
    rest_s: Range


class CardioFinisherRx(Table):
    minutes: Range
    intensity_es: str


class CommonRx(Table):
    core: CoreRx
    warmup: WarmupRx
    cooldown: CooldownRx
    cardio_finisher: CardioFinisherRx


class ExperienceAdjustment(Table):
    rir_delta: int = Field(ge=0, le=3)
    sets: Literal["min", "mid", "max"]


class MinRest(Table):
    main: int = Field(ge=0)
    accessory: int = Field(ge=0)
    core: int = Field(ge=0)

    def for_role(self, role: ExerciseRole) -> int | None:
        return {
            ExerciseRole.MAIN: self.main,
            ExerciseRole.ACCESSORY: self.accessory,
            ExerciseRole.CORE: self.core,
        }.get(role)


class TimeModel(Table):
    seconds_per_rep: float = Field(gt=0)
    transition_s: int = Field(ge=0)
    superset_transition_s: int = Field(ge=0)
    warmup_minutes: int = Field(ge=0)
    cooldown_minutes: int = Field(ge=0)
    budget_tolerance: float = Field(ge=0, le=0.5)


class BodyweightRepLimits(NameRule):
    """Techo y suelo de repeticiones en ejercicios de peso corporal muy exigentes (C9)."""

    min: int = Field(ge=1)
    max: int = Field(ge=1)

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        _check_range((self.min, self.max), "bodyweight_rep_limits")
        return self


class Prescription(Table):
    version: int
    table: dict[Goal, dict[Literal["main", "accessory"], RoleRx]]
    common: CommonRx
    experience_adjustments: dict[Experience, ExperienceAdjustment]
    min_rest_s: MinRest
    bodyweight_rep_limits: BodyweightRepLimits
    time_model: TimeModel

    @model_validator(mode="after")
    def _check_coverage(self) -> Self:
        if set(self.table) != set(Goal) or any(len(v) != 2 for v in self.table.values()):  # noqa: PLR2004
            msg = "table debe definir main y accessory para todos los objetivos"
            raise ValueError(msg)
        if set(self.experience_adjustments) != set(Experience):
            msg = "experience_adjustments debe cubrir los tres niveles"
            raise ValueError(msg)
        return self


# ------------------------------------------------------------------------ periodization
class Accumulation(Table):
    rir_by_week: tuple[int, ...] = Field(min_length=7)
    extra_sets_per_group_per_week: int = Field(ge=0)
    cap_ratio_of_max: float = Field(gt=0)


class Deload(Table):
    last_week: bool
    volume_ratio: float = Field(gt=0, le=1)
    rir: int = Field(ge=0, le=5)
    load_ratio: float = Field(gt=0, le=1)


class Phases(Table):
    accumulation: Accumulation
    deload: Deload


class UndulationDay(Table):
    reps_shift: int
    rir: int = Field(ge=0, le=5)


class HeavyDay(Table):
    reps_shift: int
    min_reps: int = Field(ge=1)
    rir_floor: dict[Experience, int]

    @model_validator(mode="after")
    def _check_levels(self) -> Self:
        if set(self.rir_floor) != set(Experience) or any(
            not 0 <= v <= MAX_TABLE_RIR for v in self.rir_floor.values()
        ):
            msg = "heavy_day.rir_floor debe cubrir los tres niveles con RIR entre 0 y 5"
            raise ValueError(msg)
        return self


class UndulationScope(Table):
    """Qué ejercicios ondulan: solo compuestos cargables con material que admite carga."""

    mechanic: Mechanic
    load_type: LoadType
    equipment_any: tuple[EquipmentCode, ...] = Field(min_length=1)

    def applies(self, card: ExerciseCard) -> bool:
        return (
            card.mechanic is self.mechanic
            and card.load_type is self.load_type
            and card.equipment_code in self.equipment_any
        )


class StrengthUndulation(Table):
    enabled_for: tuple[Experience, ...]
    applies_to: UndulationScope
    excluded_ids: tuple[str, ...] = ()
    heavy_day: HeavyDay
    medium_day: UndulationDay

    def undulates(self, card: ExerciseCard) -> bool:
        return self.applies_to.applies(card) and card.id not in self.excluded_ids


class ProgressionTable(Table):
    upper_compound_kg: float = Field(gt=0)
    lower_compound_kg: float = Field(gt=0)
    isolation_kg: float = Field(gt=0)
    miss_threshold_sessions: int = Field(ge=1)
    reduce_ratio: FloatRange
    warmup_ramp: tuple[tuple[float, int], ...] = Field(min_length=1)
    plates_kg: tuple[float, ...] = Field(min_length=1)
    bar_kg: float = Field(gt=0)


class Periodization(Table):
    version: int
    default_weeks: int
    allowed_weeks: tuple[int, ...]
    phases: Phases
    strength_undulation: StrengthUndulation
    beginner_linear: bool
    progression: ProgressionTable

    @model_validator(mode="after")
    def _check_weeks(self) -> Self:
        if self.default_weeks not in self.allowed_weeks:
            msg = "default_weeks debe estar en allowed_weeks"
            raise ValueError(msg)
        return self


# ------------------------------------------------------------------------ sex-modifiers
class SexModifier(Table):
    default_emphasis: Emphasis
    accessory_rest_multiplier: float = Field(gt=0, le=1)
    isolation_rep_max_delta: int = Field(ge=0, le=5)
    demo_variant_bonus: int = Field(ge=0)
    bmr_formula: str


class SexModifiers(Table):
    version: int
    female: SexModifier
    male: SexModifier
    unspecified: SexModifier
    explanation_es: dict[Sex, str]

    def for_sex(self, sex: Sex) -> SexModifier:
        modifier: SexModifier = getattr(self, sex.value)
        return modifier

    @model_validator(mode="after")
    def _check_explanations(self) -> Self:
        if set(self.explanation_es) != set(Sex):
            msg = "explanation_es debe cubrir los tres valores de sexo"
            raise ValueError(msg)
        return self


# --------------------------------------------------------------------- pattern-affinity
class PatternAffinity(Table):
    version: int
    affinity: dict[MovementPattern, tuple[MovementPattern, ...]]


# ----------------------------------------------------------------- normalizaciones
class EquipmentEntry(Table):
    code: EquipmentCode
    es: str
    group: EquipmentGroup


class EquipmentNormalization(Table):
    version: int
    map: dict[str, EquipmentEntry]
    presets: dict[EquipmentPreset, Literal["*"] | tuple[EquipmentCode, ...]]

    @model_validator(mode="after")
    def _check_presets(self) -> Self:
        if set(self.presets) != set(EquipmentPreset):
            msg = "presets debe cubrir todos los presets"
            raise ValueError(msg)
        return self


class CanonicalMuscle(Table):
    es: str
    en: str
    region: str
    group: MuscleGroup


class MuscleNormalization(Table):
    version: int
    canonical: dict[MuscleCode, CanonicalMuscle]
    map: dict[str, MuscleCode]

    @model_validator(mode="after")
    def _check_canonical(self) -> Self:
        if set(self.canonical) != set(MuscleCode):
            msg = "canonical debe cubrir todos los MuscleCode"
            raise ValueError(msg)
        return self


# ------------------------------------------------------------------------ engine-rules
class GoalDefaults(Table):
    include_warmup: bool
    include_cooldown: bool
    include_cardio_finisher: bool


class DifficultyRules(Table):
    cap: dict[Experience, int]
    accessory_extra: dict[Experience, int]
    relax_difficulty_for: tuple[Experience, ...] = ()

    @model_validator(mode="after")
    def _check_levels(self) -> Self:
        if set(self.cap) != set(Experience) or set(self.accessory_extra) != set(Experience):
            msg = "difficulty debe cubrir los tres niveles"
            raise ValueError(msg)
        return self


class Scoring(Table):
    pattern_exact: int
    target_group: int
    staple_in_main: int
    favorite: int
    used_other_day: int
    same_variant_group: int
    above_difficulty: int
    unilateral_in_strength_main: int
    loadable_in_main: int
    staple_in_accessory: int
    barbell_in_strength_main: int
    lower_main_barbell_or_machine: int


Relaxation = Literal["difficulty", "staple", "target_group", "pattern_affinity"]


class AllocationRules(Table):
    """Límites de series por ejercicio: main y accesorio salen de ``prescription.yaml`` (B2)."""

    core_bounds: Range
    min_sets_per_exercise: int = Field(ge=1, le=3)
    tolerance_sets: float = Field(ge=0)
    accumulation_extra_cap: int = Field(ge=0, le=3)
    accumulation_extra_from_week: int = Field(ge=1)
    volume_warning_ratio: float = Field(gt=0, lt=1)

    @model_validator(mode="after")
    def _check_bounds(self) -> Self:
        _check_range(self.core_bounds, "core_bounds")
        return self


class FixtureGated(NameRule):
    """Ejercicios que exigen estructura fija: fuera con los presets ``presets``."""

    presets: tuple[EquipmentPreset, ...] = Field(min_length=1)


class ArmsBlockRules(Table):
    goals: tuple[Goal, ...] = Field(min_length=1)
    excluded_experience: tuple[Experience, ...] = ()


class GeneralFitnessElbow(Table):
    priority: int = Field(ge=1, le=3)
    drop_from_days: int = Field(ge=1, le=8)


class WarmupRules(Table):
    cardio_share: float = Field(gt=0, le=1)
    specific_items: int = Field(ge=0, le=2)
    cardio_rotation: bool


class CooldownRules(Table):
    items: int = Field(ge=1, le=4)


class FinisherRules(Table):
    long_session_minutes: int = Field(ge=20)


class RecoveryRules(Table):
    cardio_minutes: Range
    reserve_minutes: int = Field(ge=0)
    mobility_sets: int = Field(ge=1)
    mobility_hold_s: int = Field(ge=5)
    cardio_equipment_any: tuple[EquipmentCode, ...] = Field(min_length=1)
    cardio_ids_any: tuple[str, ...] = ()


class ProgressionLoads(Table):
    plate_loaded: tuple[EquipmentCode, ...]
    step_kg: dict[str, float]
    bodyweight_rep_cap: int = Field(ge=1)
    bodyweight_rep_step: int = Field(ge=1)
    time_step_s: int = Field(ge=1)

    @model_validator(mode="after")
    def _check_steps(self) -> Self:
        if "default" not in self.step_kg or any(v <= 0 for v in self.step_kg.values()):
            msg = "step_kg necesita default y pasos positivos"
            raise ValueError(msg)
        return self

    def step_for(self, equipment: EquipmentCode) -> float:
        return self.step_kg.get(equipment.value, self.step_kg["default"])


class EngineRules(Table):
    version: int
    goal_defaults: dict[Goal, GoalDefaults]
    always_available_equipment: tuple[EquipmentCode, ...]
    difficulty: DifficultyRules
    scoring: Scoring
    loadable_equipment: dict[Experience, tuple[EquipmentCode, ...]]
    lower_main_preferred_equipment: tuple[EquipmentCode, ...]
    strength_main_preferred_equipment: dict[Experience, tuple[EquipmentCode, ...]]
    main_requires_compound: bool
    skill_gated: NameRule
    contraindicated_default: NameRule
    fixture_gated: FixtureGated
    bar_gated: FixtureGated
    advanced_strength_main_excluded_ids: tuple[str, ...] = ()
    low_quality_ids: tuple[str, ...] = ()
    lumbar_avoid: NameRule
    relaxation_order: tuple[Relaxation, ...]
    relaxations_warned: tuple[Relaxation, ...]
    max_alternatives: int = Field(ge=0, le=3)
    allocation: AllocationRules
    pattern_groups: dict[MovementPattern, MuscleGroup]
    emphasis_block_priority: int = Field(ge=1, le=3)
    arms_block: ArmsBlockRules
    general_fitness_elbow_extension: GeneralFitnessElbow
    compound_secondary_groups: dict[MovementPattern, tuple[VolumeGroup, ...]]
    antagonist_pairs: tuple[tuple[MovementPattern, MovementPattern], ...]
    warmup: WarmupRules
    cooldown: CooldownRules
    finisher: FinisherRules
    recovery: RecoveryRules
    group_names_es: dict[MuscleGroup, str]
    progression_loads: ProgressionLoads

    @model_validator(mode="after")
    def _check_coverage(self) -> Self:
        if set(self.goal_defaults) != set(Goal):
            msg = "goal_defaults debe cubrir todos los objetivos"
            raise ValueError(msg)
        if set(self.pattern_groups) != set(MovementPattern):
            msg = "pattern_groups debe cubrir todos los patrones"
            raise ValueError(msg)
        if set(self.group_names_es) != set(MuscleGroup):
            msg = "group_names_es debe cubrir todos los grupos"
            raise ValueError(msg)
        for name in ("loadable_equipment", "strength_main_preferred_equipment"):
            if set(getattr(self, name)) != set(Experience):
                msg = f"{name} debe cubrir los tres niveles"
                raise ValueError(msg)
        if sorted(self.relaxation_order) != sorted(
            ("difficulty", "staple", "target_group", "pattern_affinity")
        ) or not set(self.relaxations_warned) <= set(self.relaxation_order):
            msg = "relaxation_order debe contener cada relajación una vez"
            raise ValueError(msg)
        return self


# ----------------------------------------------------------------------------- Tables
class Tables(Table):
    """Modelo validado de todas las tablas del motor."""

    split_templates: SplitTemplates
    volume_targets: VolumeTargets
    prescription: Prescription
    periodization: Periodization
    sex_modifiers: SexModifiers
    pattern_affinity: PatternAffinity
    equipment_normalization: EquipmentNormalization
    muscle_normalization: MuscleNormalization
    engine_rules: EngineRules

    _hash: str = PrivateAttr(default="")

    def model_post_init(self, _context: Any, /) -> None:
        self._hash = _hash_tables(self)

    @property
    def tables_hash(self) -> str:
        """SHA-256 del JSON canónico de las tablas (claves ordenadas, sin espacios)."""
        return self._hash

    def muscle_group(self, muscle: MuscleCode) -> MuscleGroup:
        return self.muscle_normalization.canonical[muscle].group

    def volume_group(self, muscle: MuscleCode) -> VolumeGroup | None:
        group = self.muscle_group(muscle).value
        return VolumeGroup(group) if group in VOLUME_GROUP_VALUES else None


def _hash_tables(tables: Tables) -> str:
    payload = json.dumps(
        tables.model_dump(mode="json", by_alias=True),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


FILES: dict[str, str] = {
    "split_templates": "split-templates.yaml",
    "volume_targets": "volume-targets.yaml",
    "prescription": "prescription.yaml",
    "periodization": "periodization.yaml",
    "sex_modifiers": "sex-modifiers.yaml",
    "pattern_affinity": "pattern-affinity.yaml",
    "equipment_normalization": "equipment-normalization.yaml",
    "muscle_normalization": "muscle-normalization.yaml",
    "engine_rules": "engine-rules.yaml",
}


def _read_yaml(path: Path) -> Any:
    try:
        with path.open(encoding="utf-8") as handle:
            return yaml.safe_load(handle)
    except FileNotFoundError as exc:
        msg = f"{path.name}: no existe en {path.parent}"
        raise TablesError(msg) from exc
    except yaml.YAMLError as exc:
        msg = f"{path.name}: YAML mal formado: {exc}"
        raise TablesError(msg) from exc


def load_tables(path: Path | str = DEFAULT_SPECS_DIR) -> Tables:
    """Carga y valida todas las tablas del directorio ``path``; falla rápido si algo no cuadra."""
    base = Path(path)
    raw = {field: _read_yaml(base / name) for field, name in FILES.items()}
    try:
        return Tables.model_validate(raw)
    except ValidationError as exc:
        msg = f"tablas inválidas en {base}: {exc}"
        raise TablesError(msg) from exc


@cache
def default_tables() -> Tables:
    """Tablas de la ruta por defecto, cargadas una sola vez por proceso."""
    return load_tables(DEFAULT_SPECS_DIR)
