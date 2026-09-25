"""Los 12 perfiles representativos de los snapshots golden (§7.8) y su versión legible."""

from forja_engine.models import (
    BlockKind,
    Emphasis,
    EquipmentCode,
    EquipmentPreset,
    EquipmentSelection,
    Experience,
    GeneratorInput,
    Goal,
    MovementPattern,
    MuscleCode,
    ProgramPlan,
    Sex,
)
from forja_engine.texts import number_es
from tests.helpers import catalog


def _inp(**data: object) -> GeneratorInput:
    return GeneratorInput.model_validate({"seed": 20260923, **data})


def _eq(preset: EquipmentPreset, *items: EquipmentCode) -> EquipmentSelection:
    return EquipmentSelection(preset=preset, items=items)


PROFILES: dict[str, tuple[str, GeneratorInput]] = {
    "01-beginner-female-home-dumbbells-hypertrophy-3d": (
        "Principiante, mujer, casa con mancuernas, hipertrofia, 3 días de 45 min, énfasis "
        "preseleccionado en tren inferior y glúteo.",
        _inp(
            goal=Goal.HYPERTROPHY,
            days_per_week=3,
            sex=Sex.FEMALE,
            experience=Experience.BEGINNER,
            session_minutes=45,
            equipment=_eq(EquipmentPreset.HOME_DUMBBELLS),
            emphasis=Emphasis.LOWER_GLUTES,
        ),
    ),
    "02-intermediate-male-gym-hypertrophy-4d": (
        "Intermedio, hombre, gimnasio completo, hipertrofia, torso/pierna 4 días de 60 min.",
        _inp(
            goal=Goal.HYPERTROPHY,
            days_per_week=4,
            sex=Sex.MALE,
            experience=Experience.INTERMEDIATE,
            session_minutes=60,
            equipment=_eq(EquipmentPreset.FULL_GYM),
        ),
    ),
    "03-advanced-male-gym-hypertrophy-6d": (
        "Avanzado, hombre, gimnasio, hipertrofia, empuje/tirón/pierna dos veces, sesiones de "
        "75 min.",
        _inp(
            goal=Goal.HYPERTROPHY,
            days_per_week=6,
            sex=Sex.MALE,
            experience=Experience.ADVANCED,
            session_minutes=75,
            equipment=_eq(EquipmentPreset.FULL_GYM),
        ),
    ),
    "04-intermediate-female-gym-strength-4d": (
        "Intermedia, mujer, gimnasio, fuerza, 4 días de 60 min con día de glúteo e isquios y "
        "ondulación pesado/medio.",
        _inp(
            goal=Goal.STRENGTH,
            days_per_week=4,
            sex=Sex.FEMALE,
            experience=Experience.INTERMEDIATE,
            session_minutes=60,
            equipment=_eq(EquipmentPreset.FULL_GYM),
            emphasis=Emphasis.LOWER_GLUTES,
        ),
    ),
    "05-advanced-unspecified-gym-strength-3d": (
        "Avanzado, sexo no indicado, gimnasio, fuerza, empuje/tirón/pierna 3 días de 90 min, "
        "mesociclo de 6 semanas.",
        _inp(
            goal=Goal.STRENGTH,
            days_per_week=3,
            sex=Sex.UNSPECIFIED,
            experience=Experience.ADVANCED,
            session_minutes=90,
            equipment=_eq(EquipmentPreset.FULL_GYM),
            weeks=6,
        ),
    ),
    "06-beginner-unspecified-bodyweight-fat-loss-3d": (
        "Principiante, peso corporal, pérdida de grasa, 3 días de 30 min con finisher de cardio.",
        _inp(
            goal=Goal.FAT_LOSS,
            days_per_week=3,
            sex=Sex.UNSPECIFIED,
            experience=Experience.BEGINNER,
            session_minutes=30,
            equipment=_eq(EquipmentPreset.BODYWEIGHT),
        ),
    ),
    "07-intermediate-female-bands-toning-4d": (
        "Intermedia, mujer, casa con bandas, tonificación, 4 días de 45 min con superseries.",
        _inp(
            goal=Goal.TONING,
            days_per_week=4,
            sex=Sex.FEMALE,
            experience=Experience.INTERMEDIATE,
            session_minutes=45,
            equipment=_eq(EquipmentPreset.HOME_BANDS),
            emphasis=Emphasis.LOWER_GLUTES,
        ),
    ),
    "08-intermediate-male-bodyweight-endurance-3d": (
        "Intermedio, hombre, peso corporal, resistencia en circuito, 3 días de 40 min.",
        _inp(
            goal=Goal.ENDURANCE,
            days_per_week=3,
            sex=Sex.MALE,
            experience=Experience.INTERMEDIATE,
            session_minutes=40,
            equipment=_eq(EquipmentPreset.BODYWEIGHT),
        ),
    ),
    "09-beginner-male-gym-general-fitness-2d": (
        "Principiante, hombre, gimnasio, forma general, cuerpo completo A/B 2 días de 60 min.",
        _inp(
            goal=Goal.GENERAL_FITNESS,
            days_per_week=2,
            sex=Sex.MALE,
            experience=Experience.BEGINNER,
            session_minutes=60,
            equipment=_eq(EquipmentPreset.FULL_GYM),
        ),
    ),
    "10-advanced-female-gym-hypertrophy-5d": (
        "Avanzada, mujer, gimnasio, hipertrofia, 5 días de 60 min con énfasis en tren inferior.",
        _inp(
            goal=Goal.HYPERTROPHY,
            days_per_week=5,
            sex=Sex.FEMALE,
            experience=Experience.ADVANCED,
            session_minutes=60,
            equipment=_eq(EquipmentPreset.FULL_GYM),
            emphasis=Emphasis.LOWER_GLUTES,
        ),
    ),
    "11-intermediate-unspecified-gym-general-fitness-7d": (
        "Intermedio, gimnasio, forma general, 7 días de 45 min: incluye el día obligatorio de "
        "recuperación activa.",
        _inp(
            goal=Goal.GENERAL_FITNESS,
            days_per_week=7,
            sex=Sex.UNSPECIFIED,
            experience=Experience.INTERMEDIATE,
            session_minutes=45,
            equipment=_eq(EquipmentPreset.FULL_GYM),
        ),
    ),
    "12-intermediate-male-custom-back-limitation-5d": (
        "Intermedio, hombre, equipamiento propio (mancuernas, polea, máquinas), hipertrofia con "
        "énfasis en brazos, 5 días de 60 min, evita la bisagra de cadera y la zona lumbar.",
        _inp(
            goal=Goal.HYPERTROPHY,
            days_per_week=5,
            sex=Sex.MALE,
            experience=Experience.INTERMEDIATE,
            session_minutes=60,
            equipment=_eq(
                EquipmentPreset.CUSTOM,
                EquipmentCode.DUMBBELL,
                EquipmentCode.CABLE,
                EquipmentCode.MACHINE,
            ),
            emphasis=Emphasis.ARMS,
            avoid_patterns=(MovementPattern.HINGE,),
            avoid_muscles=(MuscleCode.LOWER_BACK,),
        ),
    ),
}

BLOCK_ES = {
    BlockKind.WARMUP: "Calentamiento",
    BlockKind.MAIN: "Trabajo",
    BlockKind.SUPERSET: "Superserie",
    BlockKind.CIRCUIT: "Circuito",
    BlockKind.FINISHER: "Finisher",
    BlockKind.COOLDOWN: "Vuelta a la calma",
}


def render_markdown(title: str, description: str, plan: ProgramPlan) -> str:
    """Semana tipo en tablas por día, volumen, descarga, avisos y explicaciones."""
    cards = {c.id: c for c in catalog()}
    lines = [f"# {title}", "", description, ""]
    inp = plan.input
    lines += [
        f"- Split: `{' / '.join(plan.split)}` · semanas: {inp.weeks} · semilla: {plan.seed}",
        f"- Equipamiento: {', '.join(inp.equipment.items)}",
        "",
        "## Semana 1 (acumulación)",
        "",
    ]
    for day in plan.weeks[0].days:
        lines += [
            f"### Día {day.index + 1} · {day.name_es} (~{day.estimated_minutes} min)",
            "",
            f"_{day.focus_es}_",
            "",
            "| Bloque | Ejercicio | Series | Reps / tiempo | RIR | Descanso | Tempo |",
            "|---|---|---|---|---|---|---|",
        ]
        for block in day.blocks:
            kind = BLOCK_ES[block.kind]
            if block.rounds > 1:
                kind += f" x{block.rounds}"
            for ex in block.exercises:
                card = cards[ex.exercise_id]
                if ex.duration_s is not None:
                    dose = f"{ex.duration_s} s"
                else:
                    dose = f"{ex.rep_min}-{ex.rep_max}"
                if ex.per_side:
                    dose += " por lado"
                rir = "—" if ex.target_rir is None else str(ex.target_rir)
                lines.append(
                    f"| {kind} | {card.name_es} ({card.id}) | {ex.sets} | {dose} | {rir} | "
                    f"{ex.rest_s} s | {ex.tempo or '—'} |"
                )
        volume = ", ".join(f"{v.group.value} {number_es(v.sets)}" for v in day.volume)
        lines += ["", f"Series efectivas: {volume or '—'}", ""]
    lines += [
        "## Progresión del mesociclo",
        "",
        "| Semana | Fase | RIR objetivo | Volumen relativo |",
        "|---|---|---|---|",
    ]
    lines += [
        f"| {w.index + 1} | {w.phase.value} | {w.target_rir} | {number_es(w.volume_ratio)} |"
        for w in plan.weeks
    ]
    lines += [
        "",
        "## Volumen semanal (semana 1)",
        "",
        "| Grupo | Objetivo | Planificado |",
        "|---|---|---|",
    ]
    lines += [
        f"| {v.group.value} | {number_es(v.target_min)}-{number_es(v.target_max)} | "
        f"{number_es(v.planned_sets)} |"
        for v in plan.weekly_volume
    ]
    lines += ["", "## Avisos", ""]
    lines += [f"- `{w.code.value}`: {w.message_es}" for w in plan.warnings] or ["- Ninguno"]
    lines += ["", "## Explicaciones (rationale_es)", ""]
    lines += [f"- {r}" for r in plan.rationale_es]
    return "\n".join(lines) + "\n"
