"""Vocabulario del dominio de catálogo según ``contracts/domain.md`` §3 (contrato v1.0.0).

Los valores se declaran como ``Literal`` para que mypy compruebe cada asignación y Pydantic
rechace cualquier valor fuera del contrato.
"""

from typing import Final, Literal, get_args

BodyPart = Literal[
    "upper_arms",
    "upper_legs",
    "back",
    "waist",
    "chest",
    "shoulders",
    "lower_legs",
    "lower_arms",
    "cardio",
    "neck",
]
EquipmentCode = Literal[
    "bodyweight",
    "dumbbell",
    "cable",
    "barbell",
    "ez_bar",
    "trap_bar",
    "machine",
    "smith",
    "sled",
    "assisted",
    "band",
    "kettlebell",
    "weighted",
    "stability_ball",
    "medicine_ball",
    "bosu",
    "rope",
    "roller",
    "ab_wheel",
    "hammer",
    "tire",
    "arm_ergometer",
    "skierg",
    "bike",
    "elliptical",
    "stepmill",
]
EquipmentGroup = Literal["gym", "home_basic", "bodyweight", "cardio_machine", "other"]
MuscleCode = Literal[
    "chest",
    "lats",
    "upper_back",
    "traps",
    "lower_back",
    "shoulders",
    "rear_delts",
    "rotator_cuff",
    "serratus",
    "biceps",
    "triceps",
    "forearms",
    "abs",
    "obliques",
    "hip_flexors",
    "glutes",
    "quads",
    "hamstrings",
    "adductors",
    "abductors",
    "calves",
    "lower_leg",
    "neck",
    "cardio",
]
MuscleRegion = Literal["upper", "lower", "core", "cardio", "other"]
MuscleGroup = Literal[
    "chest",
    "back",
    "shoulders",
    "arms",
    "quads",
    "hamstrings",
    "glutes",
    "calves",
    "core",
    "legs_other",
    "other",
    "cardio",
]
MovementPattern = Literal[
    "squat",
    "lunge",
    "hinge",
    "horizontal_push",
    "vertical_push",
    "horizontal_pull",
    "vertical_pull",
    "elbow_flexion",
    "elbow_extension",
    "shoulder_raise",
    "chest_fly",
    "rear_delt",
    "knee_extension",
    "knee_flexion",
    "hip_abduction",
    "hip_adduction",
    "glute_isolation",
    "calf",
    "core_flexion",
    "core_anti_extension",
    "core_rotation",
    "core_lateral",
    "shrug",
    "forearm",
    "neck",
    "carry",
    "plyometric",
    "cardio",
    "mobility",
    "other",
]
Mechanic = Literal["compound", "isolation"]
ExerciseRole = Literal["main", "accessory", "core", "cardio", "mobility", "warmup"]
Laterality = Literal["bilateral", "unilateral"]
DemoSex = Literal["male", "female"]
LoadType = Literal["external", "bodyweight", "assisted", "time"]
VariantKind = Literal["version", "demonstrator", "camera_angle", "duplicate"]
InstructionLang = Literal["en", "es", "it", "tr", "ru", "zh", "hi", "pl", "ko", "fr"]
IngestStatus = Literal["queued", "running", "succeeded", "failed"]

MOVEMENT_PATTERNS: Final[tuple[MovementPattern, ...]] = get_args(MovementPattern)
MAIN_PATTERNS: Final[tuple[MovementPattern, ...]] = (
    "squat",
    "lunge",
    "hinge",
    "horizontal_push",
    "vertical_push",
    "horizontal_pull",
    "vertical_pull",
)
CORE_PATTERNS: Final[frozenset[MovementPattern]] = frozenset(
    {"core_flexion", "core_anti_extension", "core_rotation", "core_lateral"}
)
# Grupos de equipamiento sobre los que se exige la matriz de staples (§6.3).
STAPLE_EQUIPMENT_GROUPS: Final[tuple[EquipmentGroup, ...]] = ("gym", "home_basic", "bodyweight")
INSTRUCTION_LANGS: Final[tuple[InstructionLang, ...]] = get_args(InstructionLang)
MIN_STAPLES_PER_CELL: Final = 2
# Celdas patrón x grupo exentas del mínimo de staples, con su motivo (revisión F1b, §5.2).
STAPLE_CELL_EXEMPTIONS: Final[dict[tuple[MovementPattern, EquipmentGroup], str]] = {
    ("vertical_push", "bodyweight"): (
        "solo existen ejercicios gimnásticos (pino y flexión en pino, dificultad 3); "
        "el motor cae por afinidad a horizontal_push"
    ),
    ("hinge", "bodyweight"): (
        "la única bisagra genuina sin material es 3292 (elevator); la bisagra sin material "
        "se cubre por afinidad con glute_isolation"
    ),
}
