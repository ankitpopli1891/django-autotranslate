"""
Tokenizers for the placeholders in Python format strings.

The printf grammar follows GNU gettext's definition of ``python-format``
(gettext-tools/src/format-python.c): ``%`` then an optional ``(key)`` (with up to one
level of nested parentheses), flags ``-+ #0``, a width (``*`` or digits), a precision (``.`` then
``*`` or digits), a length modifier ``h``, ``l`` or ``L`` and a conversion type.
``%%`` is an escape for a literal percent sign. Brace format strings
(``python-brace-format``) are tokenized with :class:`string.Formatter`, which
implements PEP 3101 exactly.
"""

import re
import string
import typing as t

from .segments import Opaque, Segment, Text, merge_text, serialize

PRINTF = re.compile(
    r"%"
    r"(?:\((?P<key>[^()]*(?:\([^()]*\)[^()]*)*)\))?"  # (key) - one level of nesting
    r"[-+ #0]*"  # flags
    r"(?:\*|\d+)?"  # width
    r"(?:\.(?:\*|\d+))?"  # precision
    r"[hlL]?"  # length modifier
    r"(?P<type>[diouxXeEfFgGcrsa%])"
)

# Used for messages without format flags (e.g. hand written catalogs). Narrower than
# PRINTF so that text like "100% sure" is not mistaken for a "% s" placeholder.
SIMPLE_PRINTF = re.compile(r"%(?:\((?P<key>\w+)\))?[-+0]?\d*(?:\.\d+)?(?P<type>[sdif])")

FormatTokenizer = t.Callable[[str], list[Segment]]

TYPE_NAMES = {
    "d": "number",
    "i": "number",
    "u": "number",
    "f": "number",
    "F": "number",
    "e": "number",
    "E": "number",
    "g": "number",
    "G": "number",
    "o": "number",
    "x": "number",
    "X": "number",
}


def _printf(text: str, pattern: re.Pattern[str]) -> list[Segment]:
    segments: list[Segment] = []
    end = 0
    for match in pattern.finditer(text):
        segments.append(Text(text[end : match.start()]))
        if match.group("type") == "%":
            segments.append(Opaque(match.group(0), "escape"))
        else:
            name = match.group("key") or TYPE_NAMES.get(match.group("type"), "item")
            segments.append(Opaque(match.group(0), "printf", name))
        end = match.end()
    segments.append(Text(text[end:]))
    return merge_text(segments)


def printf(text: str) -> list[Segment]:
    """Tokenize a ``python-format`` string."""
    return _printf(text, PRINTF)


def simple_printf(text: str) -> list[Segment]:
    """Tokenize the common printf placeholders in a message without format flags."""
    return _printf(text, SIMPLE_PRINTF)


def brace(text: str) -> list[Segment]:
    """
    Tokenize a ``python-brace-format`` string. Strings that are not valid brace
    format strings (e.g. a lone ``{``) are returned as text.
    """
    try:
        parsed = list(string.Formatter().parse(text))
    except ValueError:
        return [Text(text)]

    segments: list[Segment] = []
    cursor = 0
    for literal, field_name, _format_spec, _conversion in parsed:
        # parse() unescapes {{ and }} in the literal text, keep them as escapes so
        # they appear in the translation
        for index, part in enumerate(re.split(r"([{}])", literal)):
            if index % 2:
                segments.append(Opaque(part * 2, "escape"))
            else:
                segments.append(Text(part))
        cursor += len(literal) + sum(literal.count(c) for c in "{}")
        if field_name is not None:
            # take the field source from the input so it round trips exactly
            depth = 0
            end = cursor
            for end in range(cursor, len(text)):
                if text[end] == "{":
                    depth += 1
                elif text[end] == "}":
                    depth -= 1
                    if depth == 0:
                        break
            source = text[cursor : end + 1]
            cursor = end + 1
            name = re.split(r"[.\[]", field_name)[0] or "item"
            segments.append(
                Opaque(source, "brace", name if not name.isdigit() else "item")
            )
    merged = merge_text(segments)
    # Safety net: a tokenization that does not reproduce the input exactly would
    # change the message and corrupt translations, so treat it as plain text.
    if serialize(merged) != text:
        return [Text(text)]
    return merged


SIMPLE_BRACE = re.compile(r"(?<!\{)\{(\w*)\}(?!\})")


def simple_brace(text: str) -> list[Segment]:
    """Tokenize ``{name}`` and ``{}`` placeholders in a message without format flags."""
    segments: list[Segment] = []
    end = 0
    for match in SIMPLE_BRACE.finditer(text):
        segments.append(Text(text[end : match.start()]))
        name = match.group(1)
        segments.append(
            Opaque(
                match.group(0), "brace", "item" if not name or name.isdigit() else name
            )
        )
        end = match.end()
    segments.append(Text(text[end:]))
    return merge_text(segments)


def tokenizers_for(flags: t.Collection[str]) -> list[FormatTokenizer]:
    """
    The placeholder tokenizers for a message with the given gettext flags.

    ``python-format`` and ``python-brace-format`` enable the full grammars and
    ``no-python-format`` / ``no-python-brace-format`` disable them. If a message
    has none of these flags the common placeholders of both formats are detected.
    """
    flags = set(flags)
    known = {
        "python-format",
        "no-python-format",
        "python-brace-format",
        "no-python-brace-format",
    }
    if not flags & known:
        return [simple_printf, simple_brace]
    tokenizers: list[FormatTokenizer] = []
    if "python-format" in flags:
        tokenizers.append(printf)
    if "python-brace-format" in flags:
        tokenizers.append(brace)
    return tokenizers
