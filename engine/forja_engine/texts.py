"""Textos en español del motor: etiquetas, enumeraciones legibles y formato de cifras."""

from collections.abc import Sequence

from forja_engine.models import Emphasis, Experience, Goal, Sex

GOAL_ES: dict[Goal, str] = {
    Goal.STRENGTH: "fuerza",
    Goal.HYPERTROPHY: "hipertrofia",
    Goal.FAT_LOSS: "pérdida de grasa",
    Goal.ENDURANCE: "resistencia",
    Goal.GENERAL_FITNESS: "forma general",
    Goal.TONING: "tonificación",
}

EXPERIENCE_ES: dict[Experience, str] = {
    Experience.BEGINNER: "principiante",
    Experience.INTERMEDIATE: "intermedio",
    Experience.ADVANCED: "avanzado",
}

EMPHASIS_ES: dict[Emphasis, str] = {
    Emphasis.BALANCED: "equilibrado",
    Emphasis.LOWER_GLUTES: "tren inferior y glúteo",
    Emphasis.UPPER_BODY: "tren superior",
    Emphasis.ARMS: "brazos",
    Emphasis.BACK_POSTURE: "espalda y postura",
    Emphasis.CORE: "core",
}

SEX_ES: dict[Sex, str] = {
    Sex.MALE: "hombre",
    Sex.FEMALE: "mujer",
    Sex.UNSPECIFIED: "sin especificar",
}

SPLIT_FAMILY_ES: dict[str, str] = {
    "full_body": "cuerpo completo",
    "upper_lower": "torso/pierna",
    "push_pull_legs": "empuje/tirón/pierna",
    "glutes": "un día de glúteo e isquios",
    "recovery": "un día de recuperación activa",
}


PATTERN_ES: dict[str, str] = {
    "squat": "sentadilla",
    "lunge": "zancada",
    "hinge": "bisagra de cadera",
    "horizontal_push": "empuje horizontal",
    "vertical_push": "empuje vertical",
    "horizontal_pull": "tirón horizontal",
    "vertical_pull": "tirón vertical",
    "elbow_flexion": "flexión de codo (bíceps)",
    "elbow_extension": "extensión de codo (tríceps)",
    "shoulder_raise": "elevaciones de hombro",
    "chest_fly": "aperturas de pecho",
    "rear_delt": "deltoides posterior",
    "knee_extension": "extensión de rodilla",
    "knee_flexion": "flexión de rodilla",
    "hip_abduction": "abducción de cadera",
    "hip_adduction": "aducción de cadera",
    "glute_isolation": "glúteo aislado",
    "calf": "gemelos",
    "core_flexion": "flexión de tronco",
    "core_anti_extension": "antiextensión de core",
    "core_rotation": "rotación de core",
    "core_lateral": "core lateral",
    "shrug": "encogimientos",
    "forearm": "antebrazo",
    "neck": "cuello",
    "carry": "acarreos",
    "plyometric": "pliometría",
    "cardio": "cardio",
    "mobility": "movilidad",
    "other": "otros",
}


def join_es(items: Sequence[str]) -> str:
    """Une una lista en español: «a», «a y b», «a, b y c»."""
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " y " + items[-1]


def number_es(value: float) -> str:
    """Cifra con coma decimal y sin decimales superfluos (8 → «8», 7,5 → «7,5»)."""
    text = f"{value:.1f}".rstrip("0").rstrip(".")
    return text.replace(".", ",")


def reps_in_reserve_es(rir: int) -> str:
    """«1 repetición» / «2 repeticiones» en reserva."""
    return "1 repetición" if rir == 1 else f"{rir} repeticiones"


def seconds_es(seconds: int) -> str:
    """Duración legible: «45 s», «2 min», «2 min 30 s»."""
    minutes, rest = divmod(seconds, 60)
    if minutes == 0:
        return f"{rest} s"
    if rest == 0:
        return f"{minutes} min"
    return f"{minutes} min {rest} s"
