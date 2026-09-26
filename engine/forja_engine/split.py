"""Paso 2 (§7.2, §7.3): elegir el split y aplicar las sustituciones por énfasis."""

from dataclasses import dataclass

from forja_engine.models import (
    Emphasis,
    ExerciseRole,
    GeneratorInput,
    Goal,
    MovementPattern,
    MuscleGroup,
    SlotRef,
    Weekday,
)
from forja_engine.tables import Tables
from forja_engine.texts import EXPERIENCE_ES, SPLIT_FAMILY_ES, join_es

RECOVERY_ROLES = frozenset({ExerciseRole.CARDIO, ExerciseRole.MOBILITY})


@dataclass(frozen=True)
class DaySpec:
    """Día del split con sus slots (plantilla + bloque de énfasis)."""

    index: int
    template: str
    name_es: str
    slots: tuple[SlotRef, ...]
    is_recovery: bool
    weekday: Weekday | None


def template_family(template: str) -> str:
    """Familia de una plantilla para explicar el split en ``rationale_es``."""
    if template.startswith("full_body"):
        return "full_body"
    if template.startswith(("upper", "lower")):
        return "upper_lower"
    if template in {"push", "pull", "legs"}:
        return "push_pull_legs"
    if template == "glutes_hams":
        return "glutes"
    return "recovery"


def split_templates(inp: GeneratorInput, tables: Tables) -> list[str]:
    """Plantillas del split (tabla §7.3) tras la sustitución por énfasis."""
    split = tables.split_templates
    templates = list(split.splits[inp.days_per_week][inp.experience])
    override = split.emphasis_overrides[inp.emphasis]
    if override.with_ is not None and inp.days_per_week >= override.min_days:
        for position in range(len(templates) - 1, -1, -1):
            if templates[position] in override.replace_last_of:
                templates[position] = override.with_
                break
    return templates


def build_days(inp: GeneratorInput, tables: Tables) -> list[DaySpec]:
    """Días del split con sus slots y el día de la semana preferido, si se indicó."""
    split = tables.split_templates
    rules = tables.engine_rules
    override = split.emphasis_overrides[inp.emphasis]
    append = override.append_block if inp.days_per_week >= override.min_days else None
    if (
        append is not None
        and inp.emphasis is Emphasis.ARMS
        and (
            inp.goal not in rules.arms_block.goals
            or inp.experience in rules.arms_block.excluded_experience
        )
    ):
        append = None
    days: list[DaySpec] = []
    for index, template in enumerate(split_templates(inp, tables)):
        spec = split.day_templates[template]
        slots = [
            SlotRef(
                slot_index=i,
                pattern=slot.pattern,
                role=slot.role,
                group=slot.group,
                priority=slot.priority,
            )
            for i, slot in enumerate(spec.slots)
        ]
        is_recovery = all(slot.role in RECOVERY_ROLES for slot in slots)
        if append is not None and not is_recovery and (append.to == "*" or template in append.to):
            for pattern in append.patterns:
                priority = rules.emphasis_block_priority
                if inp.goal is Goal.GENERAL_FITNESS and pattern is MovementPattern.ELBOW_EXTENSION:
                    gf = rules.general_fitness_elbow_extension
                    if inp.days_per_week >= gf.drop_from_days:
                        continue
                    priority = gf.priority
                group = rules.pattern_groups[pattern]
                slots.append(
                    SlotRef(
                        slot_index=len(slots),
                        pattern=pattern,
                        role=ExerciseRole.CORE
                        if group is MuscleGroup.CORE
                        else ExerciseRole.ACCESSORY,
                        group=group,
                        priority=priority,
                    )
                )
        days.append(
            DaySpec(
                index=index,
                template=template,
                name_es=spec.name_es,
                slots=tuple(slots),
                is_recovery=is_recovery,
                weekday=inp.preferred_days[index] if inp.preferred_days else None,
            )
        )
    return days


def split_rationale(inp: GeneratorInput, days: list[DaySpec]) -> str:
    """Frase que explica el split elegido."""
    families: list[str] = []
    for day in days:
        family = template_family(day.template)
        if family not in families:
            families.append(family)
    described = join_es([SPLIT_FAMILY_ES[f] for f in families])
    plural = "día" if inp.days_per_week == 1 else "días"
    return (
        f"Hemos elegido un reparto de {described} porque entrenas {inp.days_per_week} "
        f"{plural} por semana y tu nivel es {EXPERIENCE_ES[inp.experience]}."
    )
