"""``generate``: orquesta los 9 pasos de §7.2 y devuelve un ``ProgramPlan`` determinista."""

from collections.abc import Callable, Collection, Iterable, Sequence
from dataclasses import dataclass, field

from pydantic import ValidationError
from pydantic_core import InitErrorDetails, PydanticCustomError

from forja_engine.allocate import SlotKey, allocate_sets, enforce_session_cap
from forja_engine.compose import (
    day_focus,
    dedupe,
    prescription_rationale,
    recovery_block_kind,
    sex_rationale,
    time_rationale,
    to_plan_day,
    volume_ratio,
    volume_warnings,
    weekly_volume,
)
from forja_engine.draft import DraftBlock, DraftDay, DraftExercise
from forja_engine.models import (
    BlockKind,
    ExerciseCard,
    ExerciseRole,
    GeneratorInput,
    MuscleGroup,
    PlanWarning,
    PlanWarningCode,
    PlanWeek,
    ProgramPlan,
    SlotRef,
)
from forja_engine.normalize import normalize_input, rng_for, safety_warnings
from forja_engine.periodize import periodization_rationale, periodize
from forja_engine.prescribe import (
    prescribe_cooldown,
    prescribe_finisher,
    prescribe_recovery,
    prescribe_warmup_cardio,
    prescribe_warmup_specific,
    prescribe_working,
)
from forja_engine.select import (
    Selector,
    UsageState,
    dropped_warning,
    relaxation_warning,
)
from forja_engine.split import DaySpec, build_days, split_rationale
from forja_engine.tables import Tables, default_tables
from forja_engine.timefit import fit_day, pair_supersets
from forja_engine.version import ENGINE_VERSION
from forja_engine.volume import Credits, card_credits, emphasis_rationale, weekly_targets


@dataclass
class BuildOptions:
    """Ajustes internos para las operaciones (regenerar un día conservando el resto)."""

    day_seeds: dict[int, int] = field(default_factory=dict)
    pre_used: Collection[ExerciseCard] = ()


class CreditCache:
    """Créditos de volumen por id de ejercicio (0 para ids desconocidos)."""

    def __init__(self, by_id: dict[str, ExerciseCard], tables: Tables) -> None:
        self.by_id = by_id
        self.tables = tables
        self.cache: dict[str, Credits] = {}

    def __call__(self, exercise_id: str) -> Credits:
        if exercise_id not in self.cache:
            card = self.by_id.get(exercise_id)
            self.cache[exercise_id] = () if card is None else card_credits(card, self.tables)
        return self.cache[exercise_id]


def _empty_pool_error(inp: GeneratorInput) -> ValidationError:
    return ValidationError.from_exception_data(
        "GeneratorInput",
        [
            InitErrorDetails(
                type=PydanticCustomError(
                    "no_exercises_available",
                    "Con el equipamiento, las exclusiones y los músculos o patrones evitados no "
                    "queda ningún ejercicio disponible.",
                ),
                loc=("equipment",),
                input=inp.model_dump(mode="json"),
            )
        ],
    )


class _Builder:
    def __init__(
        self,
        inp: GeneratorInput,
        catalog: Sequence[ExerciseCard],
        tables: Tables,
        options: BuildOptions,
    ) -> None:
        self.inp = inp
        self.tables = tables
        self.options = options
        self.selector = Selector(catalog, inp, tables)
        if self.selector.is_empty:
            raise _empty_pool_error(inp)
        self.credits = CreditCache(self.selector.by_id, tables)
        self.warnings: list[PlanWarning] = []
        self.circuit = tables.prescription.table[inp.goal]["main"].format == "circuit"
        self.supersets = tables.prescription.table[inp.goal]["accessory"].prefer_supersets
        self.week_rir = tables.periodization.phases.accumulation.rir_by_week[0]

    def build_day(self, spec: DaySpec, sets: dict[SlotKey, int], usage: UsageState) -> DraftDay:
        usage.start_day()
        seed = self.options.day_seeds.get(spec.index, self.inp.seed or 0)
        day = DraftDay(
            index=spec.index,
            template=spec.template,
            name_es=spec.name_es,
            focus_es="",
            is_recovery=spec.is_recovery,
            weekday=spec.weekday,
        )
        working: list[DraftExercise] = []
        for slot in spec.slots:
            choice = self.selector.choose(
                slot, rng_for(seed, 0, spec.index, slot.slot_index), usage
            )
            if choice is None:
                code = self.selector.missing_reason(slot, usage)
                self.warnings.append(dropped_warning(code, slot, spec.index, spec.name_es))
                continue
            warning = relaxation_warning(self.selector, slot, choice, spec.index, spec.name_es)
            if warning is not None:
                self.warnings.append(warning)
            usage.use(choice.card)
            if spec.is_recovery:
                exercise = prescribe_recovery(choice.card, slot, self.inp, self.tables)
            else:
                exercise = prescribe_working(
                    choice.card,
                    slot,
                    sets[(spec.index, slot.slot_index)],
                    self.inp,
                    self.tables,
                    week_rir=self.week_rir,
                    circuit=self.circuit,
                )
            exercise.alternatives = choice.alternatives
            working.append(exercise)
        if not working:
            working = self._fallback(spec, usage, seed)
        day.blocks = self._blocks(spec, working, usage, seed)
        day.focus_es = day_focus(day, self.tables)
        if not spec.is_recovery:
            self.warnings += enforce_session_cap(
                day,
                self.credits,
                self.tables.volume_targets.max_effective_sets_per_group_per_session,
            )
            if self.supersets and not self.circuit:
                pair_supersets(day, self.tables, self.credits, antagonists_only=False)
        self.warnings += fit_day(day, self.inp.session_minutes, self.tables, self.credits)
        return day

    def _fallback(self, spec: DaySpec, usage: UsageState, seed: int) -> list[DraftExercise]:
        """Día sin ningún slot cubierto: se usa el ejercicio disponible más útil y se avisa."""
        rng = rng_for(seed, 0, spec.index, "fallback")
        cards = self.selector.fallback_cards()
        card = rng.choice(cards)
        usage.use(card)
        role = (
            ExerciseRole.ACCESSORY
            if card.role not in {ExerciseRole.MOBILITY, ExerciseRole.CARDIO}
            else card.role
        )
        group = self.selector.group[card.id]
        slot = SlotRef(
            slot_index=0, pattern=card.movement_pattern, role=role, group=group, priority=1
        )
        self.warnings.append(
            PlanWarning(
                code=PlanWarningCode.EMPTY_DAY,
                message_es=(
                    "Con tu equipamiento y exclusiones no hemos podido completar "
                    f"«{spec.name_es}»: hemos puesto «{card.name_es}» para que no quede vacío."
                ),
                day_index=spec.index,
                exercise_id=card.id,
            )
        )
        if role is ExerciseRole.ACCESSORY:
            return [
                prescribe_working(
                    card,
                    slot,
                    3,
                    self.inp,
                    self.tables,
                    week_rir=self.week_rir,
                    circuit=self.circuit,
                )
            ]
        return [prescribe_recovery(card, slot, self.inp, self.tables)]

    def _blocks(
        self, spec: DaySpec, working: list[DraftExercise], usage: UsageState, seed: int
    ) -> list[DraftBlock]:
        if spec.is_recovery or working[0].rx_role in {ExerciseRole.MOBILITY, ExerciseRole.CARDIO}:
            return self._recovery_blocks(working)
        blocks: list[DraftBlock] = []
        warmup = self._warmup(working, usage, seed, spec.index) if self.inp.include_warmup else []
        if warmup:
            blocks.append(DraftBlock(kind=BlockKind.WARMUP, exercises=warmup))
        blocks += self._working_blocks(working)
        if self.inp.include_cardio_finisher:
            card = self.selector.finisher(rng_for(seed, 0, spec.index, "finisher"), usage)
            if card is not None:
                finisher = [prescribe_finisher(card, self.inp, self.tables)]
                blocks.append(DraftBlock(kind=BlockKind.FINISHER, exercises=finisher))
        cooldown = (
            self._cooldown(working, usage, seed, spec.index) if self.inp.include_cooldown else []
        )
        if cooldown:
            blocks.append(DraftBlock(kind=BlockKind.COOLDOWN, exercises=cooldown))
        return blocks

    @staticmethod
    def _recovery_blocks(working: list[DraftExercise]) -> list[DraftBlock]:
        blocks: list[DraftBlock] = []
        for exercise in working:
            kind = recovery_block_kind(exercise.rx_role)
            if blocks and blocks[-1].kind is kind:
                blocks[-1].exercises.append(exercise)
            else:
                blocks.append(DraftBlock(kind=kind, exercises=[exercise]))
        return blocks

    def _working_blocks(self, working: list[DraftExercise]) -> list[DraftBlock]:
        if not self.circuit:
            return [DraftBlock(kind=BlockKind.MAIN, exercises=[exercise]) for exercise in working]
        rounds = working[0].sets
        for exercise in working:
            exercise.sets = rounds
        rest = self.tables.prescription.table[self.inp.goal]["main"].rest_s[1]
        return [
            DraftBlock(
                kind=BlockKind.CIRCUIT, exercises=working, rounds=rounds, rest_between_rounds_s=rest
            )
        ]

    def _cooldown(
        self, working: list[DraftExercise], usage: UsageState, seed: int, day_index: int
    ) -> list[DraftExercise]:
        groups: list[MuscleGroup] = []
        for exercise in working:
            if exercise.slot is not None and exercise.slot.group not in groups:
                groups.append(exercise.slot.group)
        cards = self.selector.cooldown(
            groups,
            self.tables.engine_rules.cooldown.items,
            rng_for(seed, 0, day_index, "cooldown"),
            usage,
        )
        return [prescribe_cooldown(c, self.inp, self.tables) for c in cards]

    def _warmup(
        self, working: list[DraftExercise], usage: UsageState, seed: int, day_index: int
    ) -> list[DraftExercise]:
        items: list[DraftExercise] = []
        cardio = self.selector.warmup_cardio(rng_for(seed, 0, day_index, "warmup"), usage)
        if cardio is not None:
            items.append(prescribe_warmup_cardio(cardio, self.tables))
        if self.tables.engine_rules.warmup.specific_items:
            first = next((e for e in working if e.rx_role is ExerciseRole.MAIN), working[0])
            specific = self.selector.warmup_specific(
                first.card.movement_pattern, rng_for(seed, 0, day_index, "warmup-specific"), usage
            )
            if specific is not None:
                items.append(prescribe_warmup_specific(specific, self.inp, self.tables))
        return items

    def build(self) -> ProgramPlan:
        inp, tables = self.inp, self.tables
        self.warnings += safety_warnings(inp)
        specs = build_days(inp, tables)
        targets = weekly_targets(inp, tables)
        sets = allocate_sets(specs, targets, inp.goal, inp.experience, tables, circuit=self.circuit)
        usage = UsageState()
        for card in self.options.pre_used:
            usage.use(card)
        base = [self.build_day(spec, sets, usage) for spec in specs]
        drafts = periodize(base, inp, tables, targets, self.credits)
        weeks_days = [
            [to_plan_day(day, tables, self.credits) for day in week.days] for week in drafts
        ]
        weeks = tuple(
            PlanWeek(
                index=week.index,
                phase=week.phase,
                target_rir=week.target_rir,
                volume_ratio=volume_ratio(days, weeks_days[0]),
                days=tuple(days),
            )
            for week, days in zip(drafts, weeks_days, strict=True)
        )
        volume = weekly_volume(weeks_days[0], targets)
        self.warnings += volume_warnings(volume, targets, tables)
        return ProgramPlan(
            engine_version=ENGINE_VERSION,
            tables_hash=tables.tables_hash,
            seed=inp.seed or 0,
            input=inp,
            split=tuple(spec.template for spec in specs),
            weeks=weeks,
            weekly_volume=volume,
            warnings=dedupe(self.warnings),
            rationale_es=tuple(self._rationale(specs)),
        )

    def _rationale(self, specs: list[DaySpec]) -> Iterable[str]:
        inp, tables = self.inp, self.tables
        yield split_rationale(inp, specs)
        emphasis = emphasis_rationale(inp, tables)
        if emphasis is not None:
            yield emphasis
        yield prescription_rationale(inp, tables)
        yield periodization_rationale(inp, tables)
        yield time_rationale(inp)
        yield sex_rationale(inp, tables)


def build_plan(
    raw: GeneratorInput,
    catalog: Sequence[ExerciseCard],
    tables: Tables,
    options: BuildOptions | None = None,
) -> ProgramPlan:
    inp = normalize_input(raw, tables)
    return _Builder(inp, catalog, tables, options or BuildOptions()).build()


def generate(
    input: GeneratorInput,
    catalog: Sequence[ExerciseCard],
    tables: Tables | None = None,
) -> ProgramPlan:
    """Genera el programa: misma entrada + semilla + tablas ⇒ mismo plan, byte a byte."""
    return build_plan(input, catalog, tables or default_tables())


CreditsOf = Callable[[str], Credits]
