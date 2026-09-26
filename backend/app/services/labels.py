"""Etiquetas ES/EN de las facetas del catálogo que no viven en tablas (zona, patrón, rol…)."""

from typing import Final

Labels = dict[str, tuple[str, str]]

BODY_PART: Final[Labels] = {
    "upper_arms": ("Parte alta del brazo", "Upper arms"),
    "upper_legs": ("Parte alta de la pierna", "Upper legs"),
    "back": ("Espalda", "Back"),
    "waist": ("Cintura y abdomen", "Waist"),
    "chest": ("Pecho", "Chest"),
    "shoulders": ("Hombros", "Shoulders"),
    "lower_legs": ("Parte baja de la pierna", "Lower legs"),
    "lower_arms": ("Antebrazo", "Lower arms"),
    "cardio": ("Cardio", "Cardio"),
    "neck": ("Cuello", "Neck"),
}

PATTERN: Final[Labels] = {
    "squat": ("Sentadilla", "Squat"),
    "lunge": ("Zancada", "Lunge"),
    "hinge": ("Bisagra de cadera", "Hinge"),
    "horizontal_push": ("Empuje horizontal", "Horizontal push"),
    "vertical_push": ("Empuje vertical", "Vertical push"),
    "horizontal_pull": ("Tirón horizontal", "Horizontal pull"),
    "vertical_pull": ("Tirón vertical", "Vertical pull"),
    "elbow_flexion": ("Flexión de codo", "Elbow flexion"),
    "elbow_extension": ("Extensión de codo", "Elbow extension"),
    "shoulder_raise": ("Elevación de hombro", "Shoulder raise"),
    "chest_fly": ("Aperturas de pecho", "Chest fly"),
    "rear_delt": ("Deltoides posterior", "Rear delt"),
    "knee_extension": ("Extensión de rodilla", "Knee extension"),
    "knee_flexion": ("Flexión de rodilla", "Knee flexion"),
    "hip_abduction": ("Abducción de cadera", "Hip abduction"),
    "hip_adduction": ("Aducción de cadera", "Hip adduction"),
    "glute_isolation": ("Aislamiento de glúteo", "Glute isolation"),
    "calf": ("Gemelos", "Calf"),
    "core_flexion": ("Flexión de tronco", "Core flexion"),
    "core_anti_extension": ("Anti-extensión de core", "Core anti-extension"),
    "core_rotation": ("Rotación de core", "Core rotation"),
    "core_lateral": ("Core lateral", "Core lateral"),
    "shrug": ("Encogimientos", "Shrug"),
    "forearm": ("Antebrazo", "Forearm"),
    "neck": ("Cuello", "Neck"),
    "carry": ("Acarreo", "Carry"),
    "plyometric": ("Pliométrico", "Plyometric"),
    "cardio": ("Cardio", "Cardio"),
    "mobility": ("Movilidad y estiramientos", "Mobility"),
    "other": ("Otros", "Other"),
}

MECHANIC: Final[Labels] = {
    "compound": ("Multiarticular", "Compound"),
    "isolation": ("Aislamiento", "Isolation"),
}

DIFFICULTY: Final[Labels] = {
    "1": ("Básico", "Basic"),
    "2": ("Estándar", "Standard"),
    "3": ("Exigente", "Demanding"),
}

ROLE: Final[Labels] = {
    "main": ("Principal", "Main"),
    "accessory": ("Accesorio", "Accessory"),
    "core": ("Core", "Core"),
    "cardio": ("Cardio", "Cardio"),
    "mobility": ("Movilidad", "Mobility"),
    "warmup": ("Calentamiento", "Warm-up"),
}

VARIANT_LABEL_BASE: Final = "versión original"
