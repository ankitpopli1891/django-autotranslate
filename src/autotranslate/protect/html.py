"""
Tokenize HTML markup in messages (e.g. ``Read the <a href="%(url)s">docs</a>``).

Elements become :class:`.Paired` segments whose content is translated. Void and
self-closing elements, comments, declarations, character references and whole
elements in :data:`OPAQUE_ELEMENTS` are :class:`.Opaque`. Attribute values are not
translated.

The message is lexed with a regular expression and every segment's source is an
exact slice of the message, so serializing the segments always reproduces it.
"""

import re

from .segments import Opaque, Paired, Segment, Text, merge_text, serialize

#: Elements whose content must not be translated
OPAQUE_ELEMENTS = {"code", "kbd", "pre", "samp", "script", "style", "var"}

#: Elements that never have content or an end tag
VOID_ELEMENTS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}

#: A tag name
NAME = r"[A-Za-z][A-Za-z0-9:-]*"

#: One attribute of a start tag, with its optional value
ATTRIBUTE_SOURCE = r"""[^\s"'<>/=]+(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s"'=<>`]+))?"""

#: Captures the name and value (in one of three groups) of an attribute
ATTRIBUTE = re.compile(
    r"""([^\s"'<>/=]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+)))?"""
)

#: Lexes comments, declarations, tags (``start`` with ``start_name``, ``attrs`` and
#: ``slash`` or ``end`` with ``end_name``) and character references (``entity``)
LEXER = re.compile(
    rf"""
    (?P<comment><!--.*?-->)
    |(?P<declaration><!\[CDATA\[.*?\]\]>|<![^>]*>|<\?[^>]*>)
    |(?P<end></(?P<end_name>{NAME})\s*>)
    |(?P<start><(?P<start_name>{NAME})(?P<attrs>(?:\s+{ATTRIBUTE_SOURCE})*)
        \s*(?P<slash>/)?>)
    |(?P<entity>&(?:[A-Za-z][A-Za-z0-9]*|\#[0-9]+|\#[xX][0-9A-Fa-f]+);)
    """,
    re.DOTALL | re.VERBOSE,
)


class _Element:
    def __init__(self, start: Opaque | None, tag: str):
        self.start = start
        self.tag = tag
        self.children: list[Segment] = []


def html(text: str) -> list[Segment]:
    """
    Tokenize the HTML in a message. Messages that do not contain HTML are returned as
    text.
    """
    if not LEXER.search(text):
        return [Text(text)]
    try:
        return _tokenize(text)
    except RecursionError:
        # pathologically deep nesting - losing markup protection is better than failing
        return [Text(text)]


def _tokenize(text: str) -> list[Segment]:

    stack = [_Element(None, "")]

    def unwind() -> None:
        element = stack.pop()
        assert element.start is not None
        stack[-1].children.append(element.start)
        stack[-1].children.extend(element.children)

    position = 0
    for match in LEXER.finditer(text):
        if match.start() > position:
            stack[-1].children.append(Text(text[position : match.start()]))
        position = match.end()
        source = match.group()
        children = stack[-1].children
        if match["comment"] is not None:
            children.append(Opaque(source, "comment"))
        elif match["declaration"] is not None:
            children.append(Opaque(source, "declaration"))
        elif match["entity"] is not None:
            children.append(Opaque(source, "entity"))
        elif match["start"] is not None:
            tag = match["start_name"].lower()
            start = Opaque(source, "tag", tag)
            if match["slash"] or tag in VOID_ELEMENTS:
                children.append(start)
            else:
                stack.append(_Element(start, tag))
        else:
            tag = match["end_name"].lower()
            end = Opaque(source, "tag", tag)
            if not any(element.tag == tag for element in stack[1:]):
                # an end tag without a start tag
                children.append(end)
                continue
            # elements left open inside this one become loose start tags
            while stack[-1].tag != tag:
                unwind()
            element = stack.pop()
            assert element.start is not None
            if tag in OPAQUE_ELEMENTS or any(e.tag in OPAQUE_ELEMENTS for e in stack):
                stack[-1].children.append(
                    Opaque(
                        element.start.source + serialize(element.children) + source,
                        "tag",
                        tag,
                    )
                )
            else:
                stack[-1].children.append(
                    Paired(element.start, end, merge_text(element.children))
                )
    if position < len(text):
        stack[-1].children.append(Text(text[position:]))
    while len(stack) > 1:
        unwind()
    segments = merge_text(stack[0].children)
    # losing markup protection is better than corrupting the message
    return segments if serialize(segments) == text else [Text(text)]
