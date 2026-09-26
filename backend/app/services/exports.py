"""Exportaciones de un programa: PDF (WeasyPrint + Jinja2) y calendario ICS (RFC 5545)."""

import asyncio
import re
import unicodedata
import uuid
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Final
from urllib.parse import quote, unquote, urlparse

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.errors import unprocessable
from app.schemas import api

TEMPLATES: Final = Path(__file__).resolve().parent.parent / "pdf" / "templates"
ATTRIBUTION: Final = "© Gym visual — https://gymvisual.com/"
WEEKDAYS: Final = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")

TEXTS: Final[dict[str, dict[str, str]]] = {
    "es": {
        "week": "Semana",
        "phase_accumulation": "acumulación",
        "phase_intensification": "intensificación",
        "phase_deload": "descarga",
        "goal": "Objetivo",
        "days": "días por semana",
        "weeks": "semanas",
        "exercise": "Ejercicio",
        "sets": "Series",
        "reps": "Reps",
        "rir": "RIR",
        "rest": "Descanso",
        "tempo": "Tempo",
        "per_side": "por lado",
        "rounds": "rondas",
        "warnings": "Avisos",
        "why": "Por qué este programa",
        "recovery": "Recuperación activa",
        "footer": "Forja no sustituye el consejo de profesionales sanitarios ni de entrenamiento.",
        "kind_warmup": "Calentamiento",
        "kind_main": "Trabajo",
        "kind_superset": "Superserie",
        "kind_circuit": "Circuito",
        "kind_finisher": "Final",
        "kind_cooldown": "Vuelta a la calma",
    },
    "en": {
        "week": "Week",
        "phase_accumulation": "accumulation",
        "phase_intensification": "intensification",
        "phase_deload": "deload",
        "goal": "Goal",
        "days": "days per week",
        "weeks": "weeks",
        "exercise": "Exercise",
        "sets": "Sets",
        "reps": "Reps",
        "rir": "RIR",
        "rest": "Rest",
        "tempo": "Tempo",
        "per_side": "per side",
        "rounds": "rounds",
        "warnings": "Notes",
        "why": "Why this program",
        "recovery": "Active recovery",
        "footer": "Forja does not replace professional health or coaching advice.",
        "kind_warmup": "Warm-up",
        "kind_main": "Work",
        "kind_superset": "Superset",
        "kind_circuit": "Circuit",
        "kind_finisher": "Finisher",
        "kind_cooldown": "Cool-down",
    },
}


def slugify(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^A-Za-z0-9]+", "-", ascii_name).strip("-").lower()
    return slug or "programa"


def disposition(name: str, extension: str) -> str:
    """``Content-Disposition: attachment`` con nombre ASCII y variante UTF-8 (RFC 6266)."""
    return (
        f'attachment; filename="{slugify(name)}.{extension}"; '
        f"filename*=UTF-8''{quote(name, safe='')}.{extension}"
    )


# ---------------------------------------------------------------------------- PDF
def _url_fetcher(media_root: Path) -> Any:
    """Solo ``file://`` dentro de ``MEDIA_ROOT`` (miniaturas locales); nada de red."""
    from weasyprint.urls import URLFetcher, URLFetcherResponse  # noqa: PLC0415

    root = media_root.resolve()

    class LocalFetcher(URLFetcher):  # type: ignore[misc]  # weasyprint sin tipos
        def fetch(self, url: str, headers: Any = None) -> Any:
            parsed = urlparse(url)
            if parsed.scheme != "file":
                msg = f"Recurso externo no permitido en el PDF: {parsed.scheme}"
                raise ValueError(msg)
            path = Path(unquote(parsed.path)).resolve()
            if root not in path.parents:
                msg = "Ruta fuera de MEDIA_ROOT"
                raise ValueError(msg)
            return URLFetcherResponse(
                url, body=path.read_bytes(), headers={"Content-Type": "image/jpeg"}
            )

    return LocalFetcher(allowed_protocols=["file"])


def _template_context(detail: api.ProgramDetail, lang: str, media_root: Path) -> dict[str, Any]:
    names = {e.id: e for e in detail.exercises}
    thumbs = {
        e.id: (media_root / e.media.thumb_url.removeprefix("/media/")).as_uri()
        for e in detail.exercises
    }
    return {
        "program": detail,
        "t": TEXTS.get(lang, TEXTS["es"]),
        "lang": lang if lang in TEXTS else "es",
        "names": names,
        "thumbs": thumbs,
        "attribution": ATTRIBUTION,
    }


def build_pdf(detail: api.ProgramDetail, lang: str, media_root: Path) -> bytes:
    from weasyprint import HTML  # noqa: PLC0415

    env = Environment(
        loader=FileSystemLoader(TEMPLATES),
        autoescape=select_autoescape(["html", "j2"]),
    )
    html = env.get_template("program.html.j2").render(_template_context(detail, lang, media_root))
    document = HTML(string=html, base_url=media_root.as_uri(), url_fetcher=_url_fetcher(media_root))
    return document.write_pdf()  # type: ignore[no-any-return]  # weasyprint sin tipos


async def render_pdf(detail: api.ProgramDetail, lang: str, media_root: Path) -> bytes:
    return await asyncio.to_thread(build_pdf, detail, lang, media_root)


# ---------------------------------------------------------------------------- ICS
def _escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def _fold(line: str) -> str:
    """Pliega a 75 octetos (RFC 5545 §3.1) sin partir caracteres multibyte."""
    data = line.encode()
    if len(data) <= 75:  # noqa: PLR2004
        return line
    parts: list[str] = []
    current = ""
    limit = 75
    for char in line:
        if len((current + char).encode()) > limit:
            parts.append(current)
            current, limit = char, 74
        else:
            current += char
    parts.append(current)
    return "\r\n ".join(parts)


def next_monday(today: date) -> date:
    return today + timedelta(days=(7 - today.weekday()) % 7)


def _offsets(days: list[api.ProgramDay]) -> list[int]:
    """Día de la semana (0 = lunes) de cada día del programa: el preferido o repartido."""
    count = len(days)
    fallback = [round(i * 7 / count) if count else 0 for i in range(count)]
    return [
        WEEKDAYS.index(day.weekday) if day.weekday else fallback[i] for i, day in enumerate(days)
    ]


def render_ics(detail: api.ProgramDetail, start_date: date | None) -> str:
    start = start_date or next_monday(datetime.now(UTC).date())
    if start.weekday() != 0:
        raise unprocessable(
            "validation_error",
            "start_date debe ser un lunes.",
            errors=[
                {"loc": ["query", "start_date"], "msg": "Debe ser lunes", "type": "value_error"}
            ],
        )
    names = {e.id: e.name_es for e in detail.exercises}
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Forja//Programa de entrenamiento//ES",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_escape(detail.name)}",
    ]
    for week in detail.weeks:
        offsets = _offsets(week.days)
        for day, offset in zip(week.days, offsets, strict=True):
            when = start + timedelta(weeks=week.index, days=offset)
            exercises = [
                f"{names.get(ex.exercise_id, ex.exercise_id)} — {ex.sets}x"
                + (f"{ex.rep_min}-{ex.rep_max}" if ex.rep_min is not None else f"{ex.duration_s}s")
                for block in day.blocks
                for ex in block.exercises
                if block.kind in {"main", "superset", "circuit"}
            ]
            description = f"Semana {week.index + 1} ({week.phase}). " + "; ".join(exercises)
            uid = uuid.uuid5(uuid.NAMESPACE_URL, f"{detail.id}/{week.id}/{day.id}")
            lines += [
                "BEGIN:VEVENT",
                f"UID:{uid}@forja",
                f"DTSTAMP:{stamp}",
                f"DTSTART;VALUE=DATE:{when:%Y%m%d}",
                f"DTEND;VALUE=DATE:{when + timedelta(days=1):%Y%m%d}",
                f"SUMMARY:{_escape(f'Forja · {day.name}')}",
                f"DESCRIPTION:{_escape(description)}",
                "TRANSP:TRANSPARENT",
                "END:VEVENT",
            ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"
