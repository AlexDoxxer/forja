"""DTOs inmutables del motor de rutinas (``contracts/domain.md`` §3 y §5).

Todos los modelos son Pydantic v2 ``frozen=True, extra="forbid"`` y las secuencias son
``tuple[...]``; su forma JSON coincide con los esquemas homónimos de
``contracts/openapi.yaml``.
"""

from datetime import date
from enum import StrEnum
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

MAX_SEED = 9_007_199_254_740_991

ExerciseId = Annotated[str, StringConstraints(pattern=r"^[0-9]{4}$")]
Seed = Annotated[int, Field(ge=0, le=MAX_SEED)]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Tempo = Annotated[str, StringConstraints(pattern=r"^[0-9X]-[0-9X]-[0-9X]-[0-9X]$")]


class Sex(StrEnum):
    MALE = "male"
    FEMALE = "female"
    UNSPECIFIED = "unspecified"


class Experience(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class Goal(StrEnum):
    STRENGTH = "strength"
    HYPERTROPHY = "hypertrophy"
    FAT_LOSS = "fat_loss"
    ENDURANCE = "endurance"
    GENERAL_FITNESS = "general_fitness"
    TONING = "toning"


class Emphasis(StrEnum):
    BALANCED = "balanced"
    LOWER_GLUTES = "lower_glutes"
    UPPER_BODY = "upper_body"
    ARMS = "arms"
    BACK_POSTURE = "back_posture"
    CORE = "core"


class EquipmentPreset(StrEnum):
    FULL_GYM = "full_gym"
    HOME_DUMBBELLS = "home_dumbbells"
    HOME_BANDS = "home_bands"
    BODYWEIGHT = "bodyweight"
    CUSTOM = "custom"


class EquipmentCode(StrEnum):
    BODYWEIGHT = "bodyweight"
    DUMBBELL = "dumbbell"
    CABLE = "cable"
    BARBELL = "barbell"
    EZ_BAR = "ez_bar"
    TRAP_BAR = "trap_bar"
    MACHINE = "machine"
    SMITH = "smith"
    SLED = "sled"
    ASSISTED = "assisted"
    BAND = "band"
    KETTLEBELL = "kettlebell"
    WEIGHTED = "weighted"
    STABILITY_BALL = "stability_ball"
    MEDICINE_BALL = "medicine_ball"
    BOSU = "bosu"
    ROPE = "rope"
    ROLLER = "roller"
    AB_WHEEL = "ab_wheel"
    HAMMER = "hammer"
    TIRE = "tire"
    ARM_ERGOMETER = "arm_ergometer"
    SKIERG = "skierg"
    BIKE = "bike"
    ELLIPTICAL = "elliptical"
    STEPMILL = "stepmill"


class EquipmentGroup(StrEnum):
    GYM = "gym"
    HOME_BASIC = "home_basic"
    BODYWEIGHT = "bodyweight"
    CARDIO_MACHINE = "cardio_machine"
    OTHER = "other"


class MuscleCode(StrEnum):
    CHEST = "chest"
    LATS = "lats"
    UPPER_BACK = "upper_back"
    TRAPS = "traps"
    LOWER_BACK = "lower_back"
    SHOULDERS = "shoulders"
    REAR_DELTS = "rear_delts"
    ROTATOR_CUFF = "rotator_cuff"
    SERRATUS = "serratus"
    BICEPS = "biceps"
    TRICEPS = "triceps"
    FOREARMS = "forearms"
    ABS = "abs"
    OBLIQUES = "obliques"
    HIP_FLEXORS = "hip_flexors"
    GLUTES = "glutes"
    QUADS = "quads"
    HAMSTRINGS = "hamstrings"
    ADDUCTORS = "adductors"
    ABDUCTORS = "abductors"
    CALVES = "calves"
    LOWER_LEG = "lower_leg"
    NECK = "neck"
    CARDIO = "cardio"


class VolumeGroup(StrEnum):
    CHEST = "chest"
    BACK = "back"
    SHOULDERS = "shoulders"
    ARMS = "arms"
    QUADS = "quads"
    HAMSTRINGS = "hamstrings"
    GLUTES = "glutes"
    CALVES = "calves"
    CORE = "core"


class MuscleGroup(StrEnum):
    CHEST = "chest"
    BACK = "back"
    SHOULDERS = "shoulders"
    ARMS = "arms"
    QUADS = "quads"
    HAMSTRINGS = "hamstrings"
    GLUTES = "glutes"
    CALVES = "calves"
    CORE = "core"
    LEGS_OTHER = "legs_other"
    OTHER = "other"
    CARDIO = "cardio"


class BodyPart(StrEnum):
    UPPER_ARMS = "upper_arms"
    UPPER_LEGS = "upper_legs"
    BACK = "back"
    WAIST = "waist"
    CHEST = "chest"
    SHOULDERS = "shoulders"
    LOWER_LEGS = "lower_legs"
    LOWER_ARMS = "lower_arms"
    CARDIO = "cardio"
    NECK = "neck"


class MovementPattern(StrEnum):
    SQUAT = "squat"
    LUNGE = "lunge"
    HINGE = "hinge"
    HORIZONTAL_PUSH = "horizontal_push"
    VERTICAL_PUSH = "vertical_push"
    HORIZONTAL_PULL = "horizontal_pull"
    VERTICAL_PULL = "vertical_pull"
    ELBOW_FLEXION = "elbow_flexion"
    ELBOW_EXTENSION = "elbow_extension"
    SHOULDER_RAISE = "shoulder_raise"
    CHEST_FLY = "chest_fly"
    REAR_DELT = "rear_delt"
    KNEE_EXTENSION = "knee_extension"
    KNEE_FLEXION = "knee_flexion"
    HIP_ABDUCTION = "hip_abduction"
    HIP_ADDUCTION = "hip_adduction"
    GLUTE_ISOLATION = "glute_isolation"
    CALF = "calf"
    CORE_FLEXION = "core_flexion"
    CORE_ANTI_EXTENSION = "core_anti_extension"
    CORE_ROTATION = "core_rotation"
    CORE_LATERAL = "core_lateral"
    SHRUG = "shrug"
    FOREARM = "forearm"
    NECK = "neck"
    CARRY = "carry"
    PLYOMETRIC = "plyometric"
    CARDIO = "cardio"
    MOBILITY = "mobility"
    OTHER = "other"


class Mechanic(StrEnum):
    COMPOUND = "compound"
    ISOLATION = "isolation"


class ExerciseRole(StrEnum):
    MAIN = "main"
    ACCESSORY = "accessory"
    CORE = "core"
    CARDIO = "cardio"
    MOBILITY = "mobility"
    WARMUP = "warmup"


class Laterality(StrEnum):
    BILATERAL = "bilateral"
    UNILATERAL = "unilateral"


class DemoSex(StrEnum):
    MALE = "male"
    FEMALE = "female"


class LoadType(StrEnum):
    EXTERNAL = "external"
    BODYWEIGHT = "bodyweight"
    ASSISTED = "assisted"
    TIME = "time"


class Weekday(StrEnum):
    MON = "mon"
    TUE = "tue"
    WED = "wed"
    THU = "thu"
    FRI = "fri"
    SAT = "sat"
    SUN = "sun"


class WeekPhase(StrEnum):
    ACCUMULATION = "accumulation"
    INTENSIFICATION = "intensification"
    DELOAD = "deload"


class BlockKind(StrEnum):
    WARMUP = "warmup"
    MAIN = "main"
    SUPERSET = "superset"
    CIRCUIT = "circuit"
    FINISHER = "finisher"
    COOLDOWN = "cooldown"


class PlanWarningCode(StrEnum):
    BEGINNER_HIGH_FREQUENCY = "beginner_high_frequency"
    RECOVERY_DAY_ENFORCED = "recovery_day_enforced"
    SLOT_RELAXED = "slot_relaxed"
    SLOT_DROPPED = "slot_dropped"
    TIME_BUDGET_EXCEEDED = "time_budget_exceeded"
    MAIN_EXERCISE_TRIMMED = "main_exercise_trimmed"
    VOLUME_OUT_OF_RANGE = "volume_out_of_range"
    SESSION_GROUP_CAP = "session_group_cap"
    REST_BELOW_MINIMUM = "rest_below_minimum"
    EMPTY_DAY = "empty_day"
    MOBILITY_IN_MAIN_BLOCK = "mobility_in_main_block"
    EQUIPMENT_INSUFFICIENT = "equipment_insufficient"
    AVOIDED_MUSCLE_SUBSTITUTED = "avoided_muscle_substituted"
    DEPRECATED_EXERCISE = "deprecated_exercise"


class SuggestionKind(StrEnum):
    FIRST_TIME = "first_time"
    INCREASE_LOAD = "increase_load"
    INCREASE_REPS = "increase_reps"
    HARDER_VARIANT = "harder_variant"
    HOLD = "hold"
    DECREASE_LOAD = "decrease_load"


WORKING_BLOCKS: frozenset[BlockKind] = frozenset(
    {BlockKind.MAIN, BlockKind.SUPERSET, BlockKind.CIRCUIT}
)
"""Bloques cuyas series cuentan como series efectivas de trabajo."""


class Frozen(BaseModel):
    """Base de todos los DTOs: inmutables y sin campos extra."""

    model_config = ConfigDict(frozen=True, extra="forbid")


def _require_unique(values: tuple[object, ...], field: str) -> None:
    if len(set(values)) != len(values):
        msg = f"{field} no admite elementos duplicados"
        raise ValueError(msg)


class ExerciseCard(Frozen):
    """Ejercicio enriquecido del catálogo (lo exporta ``forja-ingest export-cards``)."""

    id: ExerciseId
    name_es: str
    display_name_en: str
    variant_group: str
    body_part: BodyPart
    equipment_code: EquipmentCode
    equipment_group: EquipmentGroup
    target_muscle: MuscleCode
    primary_group_muscle: MuscleCode
    secondary_muscles: tuple[MuscleCode, ...]
    movement_pattern: MovementPattern
    mechanic: Mechanic
    role: ExerciseRole
    difficulty: int = Field(ge=1, le=3)
    is_staple: bool
    laterality: Laterality
    load_type: LoadType
    demo_sex: DemoSex | None
    deprecated: bool

    @model_validator(mode="after")
    def _unique_secondaries(self) -> Self:
        _require_unique(tuple(self.secondary_muscles), "secondary_muscles")
        return self


class EquipmentSelection(Frozen):
    """Equipamiento disponible: preset del wizard y lista (resuelta en la salida)."""

    preset: EquipmentPreset
    items: tuple[EquipmentCode, ...] = ()

    @model_validator(mode="after")
    def _check_items(self) -> Self:
        _require_unique(tuple(self.items), "equipment.items")
        if self.preset is EquipmentPreset.CUSTOM and not self.items:
            msg = "con el preset custom hay que indicar al menos un equipamiento"
            raise ValueError(msg)
        return self


class GeneratorInput(Frozen):
    """Entrada del motor (MASTER_PROMPT §7.1)."""

    goal: Goal
    days_per_week: int = Field(ge=1, le=7)
    sex: Sex
    experience: Experience
    session_minutes: int = Field(ge=20, le=120, multiple_of=5)
    equipment: EquipmentSelection
    emphasis: Emphasis = Emphasis.BALANCED
    avoid_muscles: tuple[MuscleCode, ...] = ()
    avoid_patterns: tuple[MovementPattern, ...] = ()
    preferred_days: tuple[Weekday, ...] = Field(default=(), max_length=7)
    weeks: int = Field(default=5, ge=4, le=8)
    include_warmup: bool | None = None
    include_cooldown: bool | None = None
    include_cardio_finisher: bool | None = None
    favorite_exercise_ids: tuple[ExerciseId, ...] = Field(default=(), max_length=200)
    excluded_exercise_ids: tuple[ExerciseId, ...] = Field(default=(), max_length=500)
    seed: Seed | None = None

    @model_validator(mode="after")
    def _check_lists(self) -> Self:
        _require_unique(tuple(self.avoid_muscles), "avoid_muscles")
        _require_unique(tuple(self.avoid_patterns), "avoid_patterns")
        _require_unique(tuple(self.preferred_days), "preferred_days")
        _require_unique(self.favorite_exercise_ids, "favorite_exercise_ids")
        _require_unique(self.excluded_exercise_ids, "excluded_exercise_ids")
        if self.preferred_days and len(self.preferred_days) != self.days_per_week:
            msg = "preferred_days debe estar vacía o tener exactamente days_per_week elementos"
            raise ValueError(msg)
        return self


class SlotRef(Frozen):
    """Slot del día del split que originó el ejercicio."""

    slot_index: int = Field(ge=0)
    pattern: MovementPattern
    role: ExerciseRole
    group: MuscleGroup
    priority: int = Field(ge=1, le=3)


class ExercisePrescription(Frozen):
    """Prescripción de un ejercicio (reps o duración, nunca ambos ausentes)."""

    exercise_id: ExerciseId
    sets: int = Field(ge=1, le=10)
    rep_min: int | None = Field(ge=1, le=100)
    rep_max: int | None = Field(ge=1, le=100)
    duration_s: int | None = Field(ge=5, le=3600)
    per_side: bool
    target_rir: int | None = Field(ge=0, le=5)
    tempo: Tempo | None
    rest_s: int = Field(ge=0, le=600)
    load_hint: str | None = Field(max_length=200)
    notes_es: str | None = Field(max_length=500)
    alternatives: tuple[ExerciseId, ...] = Field(max_length=3)

    @model_validator(mode="after")
    def _check_prescription(self) -> Self:
        has_reps = self.rep_min is not None and self.rep_max is not None
        if (self.rep_min is None) != (self.rep_max is None):
            msg = "rep_min y rep_max se informan juntos"
            raise ValueError(msg)
        if has_reps == (self.duration_s is not None):
            msg = "exactamente uno de {rango de repeticiones, duration_s} debe informarse"
            raise ValueError(msg)
        if self.rep_min is not None and self.rep_max is not None and self.rep_min > self.rep_max:
            msg = "rep_min no puede superar rep_max"
            raise ValueError(msg)
        _require_unique(self.alternatives, "alternatives")
        return self


class PlanExercise(ExercisePrescription):
    """Ejercicio dentro de un bloque del plan."""

    order: int = Field(ge=0)
    slot: SlotRef | None


class PlanBlock(Frozen):
    """Bloque de un día: calentamiento, principal, superserie, circuito, finisher o calma."""

    order: int = Field(ge=0)
    kind: BlockKind
    rounds: int = Field(ge=1, le=10)
    rest_between_rounds_s: int | None = Field(ge=0, le=600)
    exercises: tuple[PlanExercise, ...] = Field(min_length=1)


class GroupSets(Frozen):
    """Series efectivas de un grupo de volumen en una sesión."""

    group: VolumeGroup
    sets: float = Field(ge=0, le=10)


class PlanDay(Frozen):
    """Día de entrenamiento de una semana."""

    index: int = Field(ge=0, le=6)
    template: str
    name_es: str
    focus_es: str
    weekday: Weekday | None
    is_recovery: bool
    estimated_minutes: int = Field(ge=1, le=240)
    blocks: tuple[PlanBlock, ...] = Field(min_length=1)
    volume: tuple[GroupSets, ...]


class PlanWeek(Frozen):
    """Semana del mesociclo."""

    index: int = Field(ge=0, le=7)
    phase: WeekPhase
    target_rir: int = Field(ge=0, le=5)
    volume_ratio: float = Field(gt=0, le=2)
    days: tuple[PlanDay, ...] = Field(min_length=1, max_length=7)


class GroupVolume(Frozen):
    """Series efectivas semanales objetivo y planificadas de un grupo (semana tipo)."""

    group: VolumeGroup
    target_min: float = Field(ge=0)
    target_max: float = Field(ge=0)
    planned_sets: float = Field(ge=0)


class PlanWarning(Frozen):
    """Aviso con código estable y mensaje en español."""

    code: PlanWarningCode
    message_es: str
    week_index: int | None = Field(default=None, ge=0)
    day_index: int | None = Field(default=None, ge=0, le=6)
    exercise_id: ExerciseId | None = None


class SlotAddress(Frozen):
    """Posición de un ejercicio dentro de un ``ProgramPlan``."""

    week_index: int = Field(ge=0)
    day_index: int = Field(ge=0, le=6)
    block_order: int = Field(ge=0)
    exercise_order: int = Field(ge=0)


class ProgramPlan(Frozen):
    """Salida del motor (MASTER_PROMPT §7.2 paso 9)."""

    engine_version: str
    tables_hash: Sha256
    seed: Seed
    input: GeneratorInput
    split: tuple[str, ...] = Field(min_length=1, max_length=7)
    weeks: tuple[PlanWeek, ...] = Field(min_length=4, max_length=8)
    weekly_volume: tuple[GroupVolume, ...]
    warnings: tuple[PlanWarning, ...]
    rationale_es: tuple[str, ...]


class PerformedSet(Frozen):
    """Serie registrada por el usuario (entrada de la progresión)."""

    weight_kg: float | None = Field(default=None, ge=0)
    reps: int | None = Field(default=None, ge=0)
    rir: int | None = Field(default=None, ge=0)
    duration_s: int | None = Field(default=None, ge=0)
    is_warmup: bool = False


class ExerciseHistoryEntry(Frozen):
    """Series de un ejercicio en una sesión pasada."""

    session_date: date
    sets: tuple[PerformedSet, ...]


class WarmupSet(Frozen):
    """Serie de aproximación redondeada a la carga disponible."""

    percent: float = Field(gt=0, le=1)
    reps: int = Field(ge=1)
    weight_kg: float = Field(ge=0)
    plates_per_side_kg: tuple[float, ...]


class ProgressionSuggestion(Frozen):
    """Sugerencia informativa de progresión (§7.6); el usuario siempre confirma."""

    kind: SuggestionKind
    suggested_weight_kg: float | None = Field(ge=0)
    suggested_rep_min: int | None = Field(ge=1)
    suggested_rep_max: int | None = Field(ge=1)
    suggested_exercise_id: ExerciseId | None
    plates_per_side_kg: tuple[float, ...]
    reason_es: str
    warmup_sets: tuple[WarmupSet, ...]
