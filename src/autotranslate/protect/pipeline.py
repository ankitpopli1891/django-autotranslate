"""
Protect a message's placeholders and markup while it is translated:

1. parse the message into segments (:func:`~.parse.parse`)
2. encode the segments with the service's guard (:meth:`~autotranslate.protect.guards.Guard.encode`)
3. translate the encoded text (the service)
4. decode the translation back into segments, rejecting it if opaque segments were
   lost or changed (:meth:`~autotranslate.protect.guards.Guard.decode`)
5. repair whitespace around opaque segments (:func:`~.repair.repair`)
6. join the segments into the translated message
"""

import typing as t
from collections import Counter
from dataclasses import dataclass

from .guards import Guard, same_opaques
from .parse import parse
from .repair import match_edges, repair
from .segments import Paired, Segment, serialize


@dataclass
class Protected:
    """A message prepared for translation."""

    source: str
    segments: list[Segment]
    guard: Guard
    encoded: str
    """The text to send to the translation service"""
    flags: tuple[str, ...] = ()
    """The message's gettext flags"""


def protect(text: str, guard: Guard, flags: t.Collection[str] = ()) -> Protected:
    """
    Prepare a message for translation.

    :param text: The message
    :param guard: The translation service's guard
    :param flags: The message's gettext flags (e.g. ``python-format``)
    """
    segments = parse(text, flags)
    return Protected(text, segments, guard, guard.encode(segments), tuple(flags))


def _pairs(segments: list[Segment]) -> Counter[tuple[str, str]]:
    """The (start, end) sources of every paired element, however deeply nested."""
    pairs: Counter[tuple[str, str]] = Counter()
    for segment in segments:
        if isinstance(segment, Paired):
            pairs[(segment.start.source, segment.end.source)] += 1
            pairs.update(_pairs(segment.children))
    return pairs


def restore(protected: Protected, translation: str) -> str | None:
    """
    Restore the protected placeholders and markup in a translation.

    :param protected: The prepared source message
    :param translation: The service's translation of :attr:`Protected.encoded`
    :return: The translated message, or None if the translation lost or changed
        placeholders or markup
    """
    decoded = protected.guard.decode(translation, protected.segments)
    if decoded is None:
        return None
    result = match_edges(
        protected.source, serialize(repair(protected.segments, decoded))
    )
    # text the service returned outside the guards may hold extra placeholders
    # or markup (e.g. ``(%s)`` or unescaped ``&lt;b&gt;``)
    reparsed = parse(result, protected.flags)
    if not same_opaques(protected.segments, reparsed) or _pairs(
        protected.segments
    ) != _pairs(reparsed):
        return None
    return result
