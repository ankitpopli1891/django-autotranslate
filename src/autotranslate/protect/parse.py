"""Compose the tokenizers that turn a message into segments."""

import re
import typing as t

from .formats import FormatTokenizer, tokenizers_for
from .html import html
from .segments import Opaque, Paired, Segment, Text, merge_text


def _apply(segments: list[Segment], tokenizer: FormatTokenizer) -> list[Segment]:
    """Run a tokenizer over every :class:`Text` in the segments."""
    result: list[Segment] = []
    for segment in segments:
        if isinstance(segment, Text):
            result.extend(tokenizer(segment.text))
        elif isinstance(segment, Paired):
            result.append(
                Paired(segment.start, segment.end, _apply(segment.children, tokenizer))
            )
        else:
            result.append(segment)
    return merge_text(result)


def newlines(text: str) -> list[Segment]:
    """Make newlines opaque - services in HTML mode collapse them into spaces."""
    return merge_text(
        Opaque(part, "newline") if part == "\n" else Text(part)
        for part in re.split(r"(\n)", text)
    )


def parse(text: str, flags: t.Collection[str] = ()) -> list[Segment]:
    """
    Parse a message into segments.

    :param text: The message
    :param flags: The message's gettext flags (e.g. ``python-format``), which select
        the placeholder grammars
    :return: The message's segments
    """
    segments = html(text)
    for tokenizer in [*tokenizers_for(flags), newlines]:
        segments = _apply(segments, tokenizer)
    return segments
