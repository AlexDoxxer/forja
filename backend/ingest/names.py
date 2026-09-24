"""Nombres en español (MASTER_PROMPT §6.4): cobertura, duplicados y consistencia de glosario.

``specs/overrides/names_es.json`` asigna a cada id un nombre en español sin sufijos de
variante (``(male)``, ``v. 2``, ``(back pov)``…: se gestionan como variantes). Este módulo
comprueba que:

- todos los ejercicios tienen nombre y no hay ids sobrantes;
- los nombres empiezan en minúscula (el frontend capitaliza) y no conservan sufijos;
- dos grupos de variantes distintos no comparten nombre salvo duplicado declarado;
- cada término de ``specs/glossary-es.yaml`` presente en el nombre inglés aparece traducido
  como indica el glosario, salvo excepción justificada.
"""

import re
import unicodedata
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from functools import cache
from typing import Final

from ingest.normalize import NormalizedExercise
from ingest.specs import Glossary, IngestSpecs

_STOPWORDS: Final = frozenset(
    {"a", "al", "de", "del", "el", "la", "las", "los", "en", "con", "y", "o"}
)
_SUFFIX_LEFTOVERS: Final = re.compile(r"\((?:male|female|back pov|side pov)\)|\bv\.\s*\d", re.I)
_TOKEN: Final = re.compile(r"[a-z0-9°]+")
_MIN_STEM: Final = 3


class NamesError(ValueError):
    """``names_es.json`` incompleto o incoherente con el glosario."""


@dataclass(frozen=True, slots=True)
class GlossaryTerm:
    english: str
    pattern: re.Pattern[str]
    alternatives: tuple[tuple[str, ...], ...]


@dataclass(frozen=True, slots=True)
class NamesReport:
    missing: tuple[str, ...] = ()
    unknown: tuple[str, ...] = ()
    invalid: dict[str, str] = field(default_factory=dict)
    duplicates: tuple[tuple[str, ...], ...] = ()
    glossary_violations: dict[str, tuple[str, ...]] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not (
            self.missing
            or self.unknown
            or self.invalid
            or self.duplicates
            or self.glossary_violations
        )

    def summary(self) -> str:
        parts: list[str] = []
        if self.missing:
            parts.append(f"sin nombre ES: {_shorten(self.missing)}")
        if self.unknown:
            parts.append(f"ids inexistentes: {_shorten(self.unknown)}")
        parts.extend(f"{key}: {reason}" for key, reason in sorted(self.invalid.items()))
        parts.extend(f"duplicado no declarado: {', '.join(ids)}" for ids in self.duplicates)
        parts.extend(
            f"{key}: falta traducción de {', '.join(terms)}"
            for key, terms in sorted(self.glossary_violations.items())
        )
        return "; ".join(parts)


def _shorten(ids: tuple[str, ...], limit: int = 20) -> str:
    extra = f" (+{len(ids) - limit} más)" if len(ids) > limit else ""
    return ", ".join(ids[:limit]) + extra


def fold(text: str) -> str:
    """Minúsculas sin tildes (``á`` ⇒ ``a``, ``ñ`` ⇒ ``n``)."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _stem(word: str) -> str:
    """Raíz tolerante a género y número (``inclinadas`` ⇒ ``inclinad``)."""
    if word.endswith("es") and len(word) > _MIN_STEM + 1:
        word = word[:-2]
    elif word.endswith("s") and len(word) > _MIN_STEM:
        word = word[:-1]
    if word.endswith(("o", "a")) and len(word) > _MIN_STEM:
        word = word[:-1]
    return word


def _content_words(spanish: str) -> tuple[str, ...]:
    return tuple(_stem(token) for token in _TOKEN.findall(fold(spanish)) if token not in _STOPWORDS)


def _alternatives(value: str) -> tuple[tuple[str, ...], ...]:
    """``"a / b (nota)"`` ⇒ alternativas ``a`` y ``b`` sin la nota entre paréntesis."""
    without_notes = re.sub(r"\([^)]*\)", "", value)
    return tuple(_content_words(option) for option in without_notes.split("/") if option.strip())


def _english_key(text: str) -> str:
    return " ".join(text.lower().replace("-", " ").split())


@cache
def _compile_terms(items: tuple[tuple[str, str], ...]) -> tuple[GlossaryTerm, ...]:
    ordered = sorted(items, key=lambda item: (-len(_english_key(item[0])), item[0]))
    return tuple(
        GlossaryTerm(
            english=english,
            pattern=re.compile(rf"(?<![a-z0-9]){re.escape(_english_key(english))}(?![a-z0-9])"),
            alternatives=_alternatives(spanish),
        )
        for english, spanish in ordered
    )


def glossary_terms(glossary: Glossary) -> tuple[GlossaryTerm, ...]:
    """Términos del glosario ordenados del más largo al más corto."""
    return _compile_terms(tuple(sorted(glossary.terms.items())))


def required_terms(display_name_en: str, glossary: Glossary) -> tuple[GlossaryTerm, ...]:
    """Términos presentes en el nombre inglés; los más largos consumen a los contenidos."""
    text = _english_key(display_name_en)
    found: list[GlossaryTerm] = []
    for term in glossary_terms(glossary):
        match = term.pattern.search(text)
        if match is None:
            continue
        found.append(term)
        text = text[: match.start()] + "#" * (match.end() - match.start()) + text[match.end() :]
    return tuple(found)


def glossary_violations(display_name_en: str, name_es: str, glossary: Glossary) -> tuple[str, ...]:
    """Términos del glosario cuyo equivalente español no aparece en ``name_es``."""
    available = set(_content_words(name_es))
    return tuple(
        term.english
        for term in required_terms(display_name_en, glossary)
        if not any(all(word in available for word in option) for option in term.alternatives)
    )


def _invalid_reason(name: str) -> str | None:
    if not name.strip() or name != name.strip():
        return "nombre vacío o con espacios sobrantes"
    if name[0].isupper():
        return "debe empezar en minúscula (el frontend capitaliza)"
    if _SUFFIX_LEFTOVERS.search(name):
        return "conserva un sufijo de variante"
    if "в" in name:
        return "contiene mojibake"
    return None


def _duplicate_sets(
    exercises: Sequence[NormalizedExercise], names_es: dict[str, str]
) -> Iterable[tuple[str, ...]]:
    groups_by_name: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for exercise in exercises:
        name = names_es.get(exercise.id)
        if name:
            groups_by_name[fold(name)][exercise.variant_group].append(exercise.id)
    for groups in groups_by_name.values():
        if len(groups) > 1:
            yield tuple(sorted(min(ids) for ids in groups.values()))


def validate_names(exercises: Sequence[NormalizedExercise], specs: IngestSpecs) -> NamesReport:
    """Comprueba ``names_es.json`` contra el catálogo normalizado."""
    names_es = specs.names_es
    ids = {exercise.id for exercise in exercises}
    exceptions = specs.names_exceptions
    declared = {tuple(sorted(item.ids)) for item in exceptions.intentional_duplicates}
    invalid: dict[str, str] = {}
    violations: dict[str, tuple[str, ...]] = {}
    for exercise in exercises:
        name = names_es.get(exercise.id)
        if name is None:
            continue
        reason = _invalid_reason(name)
        if reason is not None:
            invalid[exercise.id] = reason
            continue
        allowed = exceptions.glossary.get(exercise.id, {})
        missing_terms = tuple(
            term
            for term in glossary_violations(exercise.display_name_en, name, specs.glossary)
            if term not in allowed
        )
        if missing_terms:
            violations[exercise.id] = missing_terms
    duplicates = tuple(
        group for group in _duplicate_sets(exercises, names_es) if group not in declared
    )
    return NamesReport(
        missing=tuple(sorted(ids - set(names_es))),
        unknown=tuple(sorted(set(names_es) - ids)),
        invalid=invalid,
        duplicates=tuple(sorted(duplicates)),
        glossary_violations=violations,
    )


def spanish_name(exercise_id: str, specs: IngestSpecs) -> str:
    """Nombre ES de un ejercicio; su ausencia es un error de ingesta."""
    try:
        return specs.names_es[exercise_id]
    except KeyError:
        msg = f"Falta el nombre en español de {exercise_id} en specs/overrides/names_es.json"
        raise NamesError(msg) from None
