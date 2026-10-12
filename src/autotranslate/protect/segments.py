"""
The segments a message is parsed into before it is sent to a translation service.

Modelled on XLIFF's inline codes: :class:`Text` is translated, :class:`Opaque` is
never translated (XLIFF ``<ph>``) and :class:`Paired` wraps translatable content in
opaque opening and closing markup (XLIFF ``<pc>``).
"""

import typing as t
from dataclasses import dataclass, field


@dataclass
class Text:
    """Text to translate."""

    text: str


@dataclass
class Opaque:
    """
    Source text that must appear unchanged in the translation (e.g. ``%(name)s``).

    :param source: The exact source text
    :param kind: What the source is (``printf``, ``brace``, ``tag``, ``newline``,
        ...), used to choose how it is guarded
    :param name: The placeholder's name, if it has one (e.g. ``name`` for
        ``%(name)s``), which helps services that cannot be told to ignore text
    """

    source: str
    kind: str
    name: str = ""


@dataclass
class Paired:
    """
    Opaque opening and closing markup (e.g. ``<a href="...">`` and ``</a>``)
    around translatable content.
    """

    start: Opaque
    end: Opaque
    children: list["Segment"] = field(default_factory=list)


Segment = Text | Opaque | Paired


def serialize(segments: t.Iterable[Segment]) -> str:
    """Join segments back into a message."""
    parts = []
    for segment in segments:
        if isinstance(segment, Text):
            parts.append(segment.text)
        elif isinstance(segment, Opaque):
            parts.append(segment.source)
        else:
            parts.append(segment.start.source)
            parts.append(serialize(segment.children))
            parts.append(segment.end.source)
    return "".join(parts)


def flatten(segments: t.Iterable[Segment]) -> list[Segment]:
    """
    The segments as a flat list of :class:`Text` and :class:`Opaque`, with each
    :class:`Paired` expanded to its start, its children and its end.
    """
    flat: list[Segment] = []
    for segment in segments:
        if isinstance(segment, Paired):
            flat.append(segment.start)
            flat.extend(flatten(segment.children))
            flat.append(segment.end)
        else:
            flat.append(segment)
    return flat


def opaques(segments: t.Iterable[Segment]) -> t.Iterator[Opaque]:
    """Every :class:`Opaque` in the segments, in order, including paired markup."""
    for segment in flatten(segments):
        if isinstance(segment, Opaque):
            yield segment


def merge_text(segments: t.Iterable[Segment]) -> list[Segment]:
    """Join adjacent :class:`Text` segments and drop empty ones."""
    merged: list[Segment] = []
    for segment in segments:
        if isinstance(segment, Text):
            if not segment.text:
                continue
            if merged and isinstance(merged[-1], Text):
                merged[-1] = Text(merged[-1].text + segment.text)
                continue
        merged.append(segment)
    return merged
