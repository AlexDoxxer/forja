"""Paso 5 (§7.2): seleccionar ejercicios por slot con puntuación, desempate sembrado y
cadena de relajación, más calentamiento, vuelta a la calma y finisher.

El filtro base nunca depende del sexo: el sexo solo suma la bonificación de demostrador
(+5 si la variante ``(male)``/``(female)`` coincide), de modo que el conjunto de candidatos
es idéntico para cualquier valor de ``sex`` (§7.4).
"""

import random
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, field

from forja_engine.models import (
    ExerciseCard,
    ExerciseRole,
    GeneratorInput,
    Goal,
    Laterality,
    LoadType,
    MovementPattern,
    MuscleGroup,
    PlanWarning,
    PlanWarningCode,
    SlotRef,
)
from forja_engine.tables import Relaxation, Tables
from forja_engine.texts import PATTERN_ES, join_es

STRENGTH_ROLES = frozenset({ExerciseRole.MAIN, ExerciseRole.ACCESSORY, ExerciseRole.CORE})
NON_STRENGTH_ROLES = frozenset({ExerciseRole.MOBILITY, ExerciseRole.CARDIO, ExerciseRole.WARMUP})
WARMUP_ROLES = frozenset({ExerciseRole.WARMUP, ExerciseRole.CARDIO})
UNCONSTRAINED_GROUPS = frozenset({MuscleGroup.OTHER, MuscleGroup.CARDIO})


def role_compatible(slot_role: ExerciseRole, card_role: ExerciseRole) -> bool:
    """``mobility``/``cardio`` nunca en slots de fuerza; calentamiento admite cardio suave;
    slots de recuperación, su rol exacto."""
    if slot_role in STRENGTH_ROLES:
        return card_role not in NON_STRENGTH_ROLES
    if slot_role is ExerciseRole.WARMUP:
        return card_role in WARMUP_ROLES
    return card_role is slot_role


@dataclass
class UsageState:
    """Ejercicios y grupos de variante ya usados en la semana y en el día en curso."""

    week_ids: set[str] = field(default_factory=set)
    week_variants: set[str] = field(default_factory=set)
    day_ids: set[str] = field(default_factory=set)
    day_variants: set[str] = field(default_factory=set)

    def start_day(self) -> None:
        self.day_ids = set()
        self.day_variants = set()

    def use(self, card: ExerciseCard) -> None:
        self.week_ids.add(card.id)
        self.week_variants.add(card.variant_group)
        self.day_ids.add(card.id)
        self.day_variants.add(card.variant_group)


@dataclass(frozen=True)
class Choice:
    """Ejercicio elegido para un slot, sus alternativas y las relajaciones aplicadas."""

    card: ExerciseCard
    alternatives: tuple[str, ...]
    relaxed: tuple[Relaxation, ...]


class Selector:
    """Catálogo filtrado por la entrada (equipamiento, exclusiones, evitados, deprecated)."""

    def __init__(
        self, catalog: Sequence[ExerciseCard], inp: GeneratorInput, tables: Tables
    ) -> None:
        self.inp = inp
        self.tables = tables
        self.rules = tables.engine_rules
        self.by_id = {card.id: card for card in catalog}
        excluded = set(inp.excluded_exercise_ids)
        available = set(inp.equipment.items)
        self.favorites = set(inp.favorite_exercise_ids)
        self.demo_bonus = tables.sex_modifiers.for_sex(inp.sex).demo_variant_bonus
        self.usable: dict[MovementPattern, list[ExerciseCard]] = {}
        self.available: dict[MovementPattern, list[ExerciseCard]] = {}
        self.group: dict[str, MuscleGroup] = {}
        for card in sorted(catalog, key=lambda c: c.id):
            if (
                card.deprecated
                or card.id in excluded
                or card.target_muscle in inp.avoid_muscles
                or card.movement_pattern in inp.avoid_patterns
            ):
                continue
            self.group[card.id] = tables.muscle_group(card.target_muscle)
            self.usable.setdefault(card.movement_pattern, []).append(card)
            if card.equipment_code in available:
                self.available.setdefault(card.movement_pattern, []).append(card)

    @property
    def is_empty(self) -> bool:
        return not self.available

    def cap_for(self, role: ExerciseRole) -> int:
        cap = self.rules.difficulty.cap[self.inp.experience]
        if role is not ExerciseRole.MAIN:
            cap += self.rules.difficulty.accessory_extra[self.inp.experience]
        return cap

    def candidates(
        self,
        slot: SlotRef,
        relaxed: Collection[Relaxation],
        usage: UsageState,
        exclude: Collection[str] = (),
        *,
        any_equipment: bool = False,
    ) -> list[ExerciseCard]:
        """Candidatos válidos para ``slot`` con las relajaciones indicadas (ordenados por id)."""
        source = self.usable if any_equipment else self.available
        patterns = [slot.pattern]
        if "pattern_affinity" in relaxed:
            patterns += list(self.tables.pattern_affinity.affinity.get(slot.pattern, ()))
        cap = self.cap_for(slot.role)
        result: list[ExerciseCard] = []
        for pattern in patterns:
            for card in source.get(pattern, ()):
                if (
                    not role_compatible(slot.role, card.role)
                    or card.id in usage.day_ids
                    or card.id in exclude
                    or card.variant_group in usage.day_variants
                    or ("difficulty" not in relaxed and card.difficulty > cap)
                    or (
                        "staple" not in relaxed
                        and slot.role is ExerciseRole.MAIN
                        and not card.is_staple
                    )
                    or (
                        "target_group" not in relaxed
                        and slot.group not in UNCONSTRAINED_GROUPS
                        and self.group[card.id] is not slot.group
                    )
                ):
                    continue
                result.append(card)
        return sorted(result, key=lambda c: c.id)

    def score(self, card: ExerciseCard, slot: SlotRef, usage: UsageState) -> int:
        """Puntuación de §7.2 paso 5 (pesos en ``engine-rules.yaml#scoring``)."""
        weights = self.rules.scoring
        total = 0
        if card.movement_pattern is slot.pattern:
            total += weights.pattern_exact
        if self.group[card.id] is slot.group:
            total += weights.target_group
        if slot.role is ExerciseRole.MAIN and card.is_staple:
            total += weights.staple_in_main
        if card.id in self.favorites:
            total += weights.favorite
        if card.demo_sex is not None and card.demo_sex.value == self.inp.sex.value:
            total += self.demo_bonus
        if card.id in usage.week_ids:
            total += weights.used_other_day
        if card.variant_group in usage.week_variants:
            total += weights.same_variant_group
        if card.difficulty > self.rules.difficulty.cap[self.inp.experience]:
            total += weights.above_difficulty
        if (
            card.laterality is Laterality.UNILATERAL
            and slot.role is ExerciseRole.MAIN
            and self.inp.goal is Goal.STRENGTH
        ):
            total += weights.unilateral_in_strength_main
        if slot.role is ExerciseRole.MAIN and card.equipment_code in self.rules.loadable_equipment:
            total += weights.loadable_in_main
        return total

    def choose(
        self,
        slot: SlotRef,
        rng: random.Random,
        usage: UsageState,
        exclude: Collection[str] = (),
    ) -> Choice | None:
        """Mejor candidato del primer nivel de relajación con candidatos; ``None`` si no hay."""
        order = self.rules.relaxation_order
        for level in range(len(order) + 1):
            relaxed = order[:level]
            pool = self.candidates(slot, relaxed, usage, exclude)
            if not pool:
                continue
            scored = [(self.score(card, slot, usage), card) for card in pool]
            best = max(score for score, _ in scored)
            card = rng.choice([c for score, c in scored if score == best])
            alternatives: list[str] = []
            seen = {card.variant_group}
            for _, other in sorted(scored, key=lambda item: (-item[0], item[1].id)):
                if len(alternatives) == self.rules.max_alternatives:
                    break
                if other.variant_group not in seen:
                    alternatives.append(other.id)
                    seen.add(other.variant_group)
            return Choice(card=card, alternatives=tuple(alternatives), relaxed=relaxed)
        return None

    def missing_reason(self, slot: SlotRef, usage: UsageState) -> PlanWarningCode:
        """Por qué no hay candidatos: equipamiento (habría con otro material) o nada válido."""
        all_relaxed = self.rules.relaxation_order
        if self.candidates(slot, all_relaxed, usage, any_equipment=True):
            return PlanWarningCode.EQUIPMENT_INSUFFICIENT
        return PlanWarningCode.SLOT_DROPPED

    def slot_touches_avoided(self, slot: SlotRef) -> bool:
        return slot.pattern in self.inp.avoid_patterns or any(
            self.tables.muscle_group(muscle) is slot.group for muscle in self.inp.avoid_muscles
        )

    # ------------------------------------------------------------- bloques auxiliares
    def _pick(
        self, cards: list[ExerciseCard], rng: random.Random, key: Mapping[str, tuple[int, ...]]
    ) -> ExerciseCard | None:
        if not cards:
            return None
        best = min(key[c.id] for c in cards)
        return rng.choice([c for c in cards if key[c.id] == best])

    def _all_available(self) -> list[ExerciseCard]:
        return sorted(
            (card for cards in self.available.values() for card in cards), key=lambda c: c.id
        )

    def fallback_cards(self) -> list[ExerciseCard]:
        """Todo el catálogo disponible, para el día que no ha podido cubrir ningún slot."""
        return self._all_available()

    def warmup_cardio(self, rng: random.Random, usage: UsageState) -> ExerciseCard | None:
        """Cardio suave de calentamiento (se prefieren los de rol ``warmup``, p. ej. marcha)."""
        cards = [
            c
            for c in self._all_available()
            if c.role in WARMUP_ROLES
            and c.movement_pattern is MovementPattern.CARDIO
            and c.id not in usage.day_ids
        ]
        key = {c.id: (0 if c.role is ExerciseRole.WARMUP else 1, c.difficulty) for c in cards}
        return self._pick(cards, rng, key)

    def warmup_specific(
        self, pattern: MovementPattern, rng: random.Random, usage: UsageState
    ) -> ExerciseCard | None:
        """Versión ligera (peso corporal, banda o dificultad 1) del primer patrón principal."""
        cards = [
            c
            for c in self.available.get(pattern, ())
            if c.role in STRENGTH_ROLES
            and c.id not in usage.day_ids
            and c.variant_group not in usage.day_variants
            and (
                c.load_type in {LoadType.BODYWEIGHT, LoadType.ASSISTED}
                or c.equipment_code.value == "band"
                or c.difficulty == 1
            )
        ]
        key = {c.id: (c.difficulty,) for c in cards}
        return self._pick(cards, rng, key)

    def cooldown(
        self, groups: Sequence[MuscleGroup], count: int, rng: random.Random, usage: UsageState
    ) -> list[ExerciseCard]:
        """Estiramientos de los grupos trabajados en el día (y, si faltan, de cualquier grupo)."""
        mobility = [
            c
            for c in self._all_available()
            if c.role is ExerciseRole.MOBILITY and c.id not in usage.day_ids
        ]
        chosen: list[ExerciseCard] = []
        for wanted in [*groups, None]:
            while len(chosen) < count:
                taken = {c.variant_group for c in chosen}
                options = [
                    c
                    for c in mobility
                    if c.variant_group not in taken
                    and (wanted is None or self.group[c.id] is wanted)
                ]
                pick = self._pick(options, rng, {c.id: (c.difficulty,) for c in options})
                if pick is None:
                    break
                chosen.append(pick)
                if wanted is not None:
                    break
        return chosen

    def finisher(self, rng: random.Random, usage: UsageState) -> ExerciseCard | None:
        """Cardio para el finisher (distinto del cardio de calentamiento del día)."""
        cards = [
            c
            for c in self._all_available()
            if c.role is ExerciseRole.CARDIO and c.id not in usage.day_ids
        ]
        return self._pick(cards, rng, {c.id: (0,) for c in cards})


def relaxation_warning(
    selector: Selector, slot: SlotRef, choice: Choice, day_index: int, day_name: str
) -> PlanWarning | None:
    """Aviso de un slot relajado (o sustituido por músculo/patrón evitado)."""
    pattern = PATTERN_ES[slot.pattern.value]
    if selector.slot_touches_avoided(slot) and choice.relaxed:
        return PlanWarning(
            code=PlanWarningCode.AVOIDED_MUSCLE_SUBSTITUTED,
            message_es=(
                f"En «{day_name}» hemos sustituido el hueco de {pattern} por "
                f"«{choice.card.name_es}» para respetar los músculos y movimientos que "
                "quieres evitar."
            ),
            day_index=day_index,
            exercise_id=choice.card.id,
        )
    warned = [r for r in choice.relaxed if r in selector.rules.relaxations_warned]
    if not warned:
        return None
    details = {
        "difficulty": "una dificultad superior a tu nivel",
        "target_group": "otro músculo objetivo",
        "pattern_affinity": "un patrón de movimiento afín",
    }
    detail = join_es([details[relaxation] for relaxation in warned])
    return PlanWarning(
        code=PlanWarningCode.SLOT_RELAXED,
        message_es=(
            f"En «{day_name}» no había un ejercicio ideal de {pattern} con tu equipamiento: "
            f"hemos elegido «{choice.card.name_es}», con {detail}."
        ),
        day_index=day_index,
        exercise_id=choice.card.id,
    )


def dropped_warning(
    code: PlanWarningCode, slot: SlotRef, day_index: int, day_name: str
) -> PlanWarning:
    pattern = PATTERN_ES[slot.pattern.value]
    reason = (
        "con el equipamiento que tienes"
        if code is PlanWarningCode.EQUIPMENT_INSUFFICIENT
        else "que respete tus exclusiones"
    )
    return PlanWarning(
        code=code,
        message_es=(
            f"En «{day_name}» no hay ningún ejercicio de {pattern} {reason}: hemos quitado ese "
            "hueco del día."
        ),
        day_index=day_index,
    )
