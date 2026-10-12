"""
Repair the whitespace services insert or remove around opaque segments.

Services translating HTML add spaces between markup and punctuation (``{file} :``,
`` ` {name} ` ``) and sometimes drop the space between a word and markup
(``Salvo%s``). The source tells us which is right: whitespace next to an opaque
segment is removed where the source had none before punctuation, and restored
where the source had a space between a word and the segment.
"""

import unicodedata

from .segments import Opaque, Paired, Segment, Text, flatten, merge_text

# scripts that are written without spaces between words
NO_SPACE_SCRIPTS = (
    "CJK",
    "HIRAGANA",
    "KATAKANA",
    "THAI",
    "LAO",
    "KHMER",
    "MYANMAR",
    "TIBETAN",
)


# only ordinary whitespace is repaired: no-break spaces (U+00A0, U+202F) are
# deliberate, e.g. French typography (``« %s »``, ``{file} :``)
SPACES = " \t\r\n\f\v"


def _is_punctuation(char: str) -> bool:
    return unicodedata.category(char)[0] in "PS"


def _attaches(char: str, source: str, opening: bool) -> bool:
    """
    May whitespace between an opaque segment and this punctuation be removed?

    :param char: The punctuation next to the opaque segment in the translation
    :param source: The character next to the opaque segment in the source
    :param opening: True if the punctuation is before the opaque segment
    """
    if not _is_punctuation(char):
        return False
    if char == source:
        return True
    # quotation marks open or close depending on the language (German closes with
    # “), and brackets only attach on their inner side
    category = unicodedata.category(char)
    return category not in ("Pi", "Pf", "Pe" if opening else "Ps")


def _is_spaced_letter(char: str) -> bool:
    if not unicodedata.category(char).startswith("L"):
        return False
    name = unicodedata.name(char, "")
    return not name.startswith(NO_SPACE_SCRIPTS)


def _context(
    segments: list[Segment],
) -> dict[int, tuple[str, str, int | None, int | None]]:
    """
    For each opaque segment (by identity), the source text immediately before and
    after it: "" for whitespace or the string edge, else the neighbouring character.
    A space between a word and the segment is recorded as " ". The identities of
    directly adjacent opaque segments are recorded too.
    """
    flat = flatten(segments)
    context = {}
    for index, segment in enumerate(flat):
        if not isinstance(segment, Opaque):
            continue
        before = flat[index - 1] if index else None
        after = flat[index + 1] if index + 1 < len(flat) else None
        left = right = ""
        left_id = right_id = None
        if isinstance(before, Text) and before.text:
            left = " " if before.text[-1].isspace() else before.text[-1]
        elif (
            isinstance(before, Opaque)
            and before.kind == "newline"
            and segment.kind != "newline"
        ):
            # newlines are whitespace, whether sent as text or as markup
            left = " "
        elif isinstance(before, Opaque):
            left = "<"
            left_id = id(before)
        if isinstance(after, Text) and after.text:
            right = " " if after.text[0].isspace() else after.text[0]
        elif (
            isinstance(after, Opaque)
            and after.kind == "newline"
            and segment.kind != "newline"
        ):
            right = " "
        elif isinstance(after, Opaque):
            right = ">"
            right_id = id(after)
        context[id(segment)] = (left, right, left_id, right_id)
    return context


def repair(source: list[Segment], translation: list[Segment]) -> list[Segment]:
    """
    Repair the whitespace around the opaque segments in a decoded translation.

    :param source: The source message's segments
    :param translation: The decoded translation's segments, whose opaque segments
        are the source's (see :meth:`~autotranslate.protect.guards.Guard.decode`)
    :return: The repaired translation segments
    """
    context = _context(source)

    def fix(segments: list[Segment]) -> list[Segment]:
        flat = flatten(segments)
        texts = {id(seg): seg.text for seg in flat if isinstance(seg, Text)}
        for index, segment in enumerate(flat):
            if not isinstance(segment, Opaque) or id(segment) not in context:
                continue
            left, right, left_id, right_id = context[id(segment)]
            before = flat[index - 1] if index else None
            after = flat[index + 1] if index + 1 < len(flat) else None
            for gap, other, expected in (
                (index - 1, index - 2, left_id),
                (index + 1, index + 2, right_id),
            ):
                # the source had no space between these adjacent opaque segments
                if (
                    expected is not None
                    and 0 <= gap < len(flat)
                    and 0 <= other < len(flat)
                    and isinstance(flat[gap], Text)
                    and id(flat[other]) == expected
                    and not texts[id(flat[gap])].strip(SPACES)
                ):
                    texts[id(flat[gap])] = ""
            if segment.kind == "newline":
                # services add spaces around the <br> newlines are sent as
                if isinstance(before, Text) and left != " ":
                    texts[id(before)] = texts[id(before)].rstrip(" \t")
                if isinstance(after, Text) and right != " ":
                    texts[id(after)] = texts[id(after)].lstrip(" \t")
                continue
            if isinstance(before, Text):
                text = texts[id(before)]
                stripped = text.rstrip(" \t")
                if (
                    left not in ("", " ")
                    and stripped
                    and stripped != text
                    and _attaches(stripped[-1], left, opening=True)
                ):
                    # "` {name}" -> "`{name}"
                    text = stripped
                elif left == " " and text and _is_spaced_letter(text[-1]):
                    # "Salvo%s" -> "Salvo %s"
                    text += " "
                texts[id(before)] = text
            if isinstance(after, Text):
                text = texts[id(after)]
                stripped = text.lstrip(" \t")
                if (
                    right not in ("", " ")
                    and stripped
                    and stripped != text
                    and _attaches(stripped[0], right, opening=False)
                ):
                    # "{file} :" -> "{file}:"
                    text = stripped
                elif right == " " and text and _is_spaced_letter(text[0]):
                    text = " " + text
                texts[id(after)] = text
        return _rebuild(segments, texts)

    return fix(translation)


def _rebuild(segments: list[Segment], texts: dict[int, str]) -> list[Segment]:
    rebuilt: list[Segment] = []
    for segment in segments:
        if isinstance(segment, Text):
            rebuilt.append(Text(texts.get(id(segment), segment.text)))
        elif isinstance(segment, Paired):
            rebuilt.append(
                Paired(segment.start, segment.end, _rebuild(segment.children, texts))
            )
        else:
            rebuilt.append(segment)
    return merge_text(rebuilt)


def match_edges(source: str, translation: str) -> str:
    """Give the translation the source's leading and trailing whitespace."""
    if not source.strip():
        return source
    leading = source[: len(source) - len(source.lstrip())]
    trailing = source[len(source.rstrip()) :]
    return leading + translation.strip() + trailing
