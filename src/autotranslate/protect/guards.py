"""
Guards protect opaque segments while a message is translated.

A guard encodes a message's segments into the text sent to a service and decodes
the service's translation back into segments. :meth:`~autotranslate.protect.guards.Guard.decode` returns None if
the translation's opaque segments do not match the source's.
"""

import html as html_lib
import re
from collections import Counter

from .html import ATTRIBUTE, LEXER, VOID_ELEMENTS
from .segments import Opaque, Paired, Segment, Text, flatten, merge_text, opaques


class Guard:
    """Base class for guards."""

    #: The content type the encoded text is in: ``text`` or ``html``
    content_type: str = "text"

    def encode(self, segments: list[Segment]) -> str:
        """
        Encode a message's segments into the text sent to the translation service.

        :param segments: The message's segments
        :return: The text to translate
        """
        raise NotImplementedError

    def decode(self, translation: str, segments: list[Segment]) -> list[Segment] | None:
        """
        Decode the service's translation of :meth:`encode`'s text back into segments.

        :param translation: The service's translation
        :param segments: The source message's segments
        :return: The translation's segments, or None if its opaque segments do not
            match the source's
        """
        raise NotImplementedError


def same_opaques(source: list[Segment], translation: list[Segment]) -> bool:
    """
    Do the translation's opaque segments match the source's? Order may differ
    because translations may reorder words.
    """

    def count(segments):
        return Counter(
            (opaque.kind, opaque.source)
            for opaque in opaques(segments)
            if opaque.kind != "newline"
        )

    return count(source) == count(translation)


class TokenGuard(Guard):
    """
    For services that only translate plain text. Each opaque segment is replaced
    with a numbered, word-like token (``__x0__``, ``__x1__``, ...). Newlines are sent
    as is. Tokens are restored by number, and the translation is rejected if a token
    is lost or duplicated or its markup is not properly nested.

    Tokens are numbered rather than named after placeholders (``__name__``) because
    services translate tokens that are words: Google translated ``__service__`` into
    Slovenian as ``__storitev__``.
    """

    TOKEN = re.compile(r"__(\w+?)__")

    def _tokens(self, segments: list[Segment]) -> list[tuple[str, Opaque]]:
        flat = flatten(segments)
        # tokens already in the source's text must not collide with ours
        taken = {
            match.group(1).lower()
            for segment in flat
            if isinstance(segment, Text)
            for match in self.TOKEN.finditer(segment.text)
        }
        tokens = []
        number = 0
        for segment in flat:
            if not isinstance(segment, Opaque) or segment.kind == "newline":
                continue
            while f"x{number}" in taken:
                number += 1
            tokens.append((f"x{number}", segment))
            number += 1
        return tokens

    def encode(self, segments: list[Segment]) -> str:
        tokens = iter(self._tokens(segments))
        parts = []
        for segment in flatten(segments):
            if isinstance(segment, Text):
                parts.append(segment.text)
            elif isinstance(segment, Opaque) and segment.kind == "newline":
                parts.append(segment.source)
            else:
                parts.append(f"__{next(tokens)[0]}__")
        return "".join(parts)

    def decode(self, translation: str, segments: list[Segment]) -> list[Segment] | None:
        remaining = self._tokens(segments)
        known = {token for token, _ in remaining}
        starts: dict[int, Paired] = {}
        ends: dict[int, Paired] = {}

        def index(items: list[Segment]) -> None:
            for item in items:
                if isinstance(item, Paired):
                    starts[id(item.start)] = ends[id(item.end)] = item
                    index(item.children)

        index(segments)
        # open elements and the content decoded inside each
        stack: list[tuple[Paired | None, list[Segment]]] = [(None, [])]

        def place(segment: Segment) -> bool:
            if isinstance(segment, Opaque) and id(segment) in starts:
                stack.append((starts[id(segment)], []))
            elif isinstance(segment, Opaque) and id(segment) in ends:
                paired, children = stack[-1]
                if paired is None or paired is not ends[id(segment)]:
                    # an end tag out of order
                    return False
                stack.pop()
                stack[-1][1].append(
                    Paired(paired.start, paired.end, merge_text(children))
                )
            else:
                stack[-1][1].append(segment)
            return True

        end = 0
        for match in self.TOKEN.finditer(translation):
            name = match.group(1).lower()
            if name not in known:
                continue
            position = next(
                (idx for idx, (token, _) in enumerate(remaining) if token == name),
                None,
            )
            if position is None:
                # the service duplicated a token
                return None
            place(Text(translation[end : match.start()]))
            if not place(remaining.pop(position)[1]):
                return None
            end = match.end()
        place(Text(translation[end:]))
        if len(stack) != 1:
            # markup left open
            return None
        decoded = merge_text(stack[0][1])
        return decoded if same_opaques(segments, decoded) else None


def _id(attrs: str) -> str | None:
    """The value of the id attribute in a start tag's attributes, if any."""
    for match in ATTRIBUTE.finditer(attrs):
        if match.group(1).lower() == "id":
            value = next((g for g in match.groups()[1:] if g is not None), "")
            return html_lib.unescape(value)
    return None


class _HTMLDecoder:
    """
    Map a service's HTML output back onto the source segments by id.

    The output is lexed with a regular expression rather than
    :class:`html.parser.HTMLParser`, which drops text after a raw ``<`` on some
    Python versions. Anything that is not a well formed tag, comment or
    declaration is text.
    """

    def __init__(self, by_id: dict[str, Segment]):
        self.by_id = by_id
        self.stack: list[tuple[str, Segment | None, list[Segment]]] = [("", None, [])]
        self.used: set[str] = set()
        self.ok = True

    def _take(self, attrs: str) -> Segment | None:
        id_ = _id(attrs)
        if id_ is None or id_ not in self.by_id:
            return None
        if id_ in self.used:
            # the service duplicated the markup
            self.ok = False
            return None
        self.used.add(id_)
        return self.by_id[id_]

    def _start(self, tag: str, attrs: str, slash: bool) -> None:
        segment = self._take(attrs)
        if slash or tag in VOID_ELEMENTS:
            if segment is None:
                # unknown void elements added by the service are dropped
                return
            # only opaque segments, and for <br> only newlines, may be void
            if not isinstance(segment, Opaque) or (
                tag == "br" and segment.kind != "newline"
            ):
                self.ok = False
                return
            self.stack[-1][2].append(segment)
            return
        # unknown tags added by the service are dropped, keeping their text
        self.stack.append((tag, segment, []))

    def _end(self, tag: str) -> None:
        if tag in VOID_ELEMENTS or len(self.stack) == 1:
            return
        _tag, segment, children = self.stack.pop()
        if isinstance(segment, Opaque):
            # the service's copy of the opaque text is ignored
            self.stack[-1][2].append(segment)
        elif isinstance(segment, Paired):
            self.stack[-1][2].append(
                Paired(segment.start, segment.end, merge_text(children))
            )
        else:
            self.stack[-1][2].extend(children)

    def _text(self, data: str) -> None:
        if data and not any(isinstance(entry[1], Opaque) for entry in self.stack):
            self.stack[-1][2].append(Text(html_lib.unescape(data)))

    def feed(self, translation: str) -> list[Segment] | None:
        end = 0
        for match in LEXER.finditer(translation):
            if match.group("entity"):
                # entities stay in the text, which is unescaped
                continue
            self._text(translation[end : match.start()])
            end = match.end()
            if match.group("start_name"):
                self._start(
                    match.group("start_name").lower(),
                    match.group("attrs"),
                    bool(match.group("slash")),
                )
            elif match.group("end_name"):
                self._end(match.group("end_name").lower())
        self._text(translation[end:])
        if not self.ok or len(self.stack) != 1:
            return None
        return merge_text(self.stack[0][2])


# a whitespace delimited word containing an ampersand followed by a name or number
_AMPERSAND_WORD = re.compile(r"[^\s<>]*&[A-Za-z0-9#][^\s<>]*")

# the kind of the opaque segments HTMLGuard wraps such words in while translating
AMPERSAND = "ampersand"


def _unwrap_ampersands(segments: list[Segment]) -> list[Segment]:
    """Turn the ampersand words HTMLGuard protected back into text."""
    unwrapped: list[Segment] = []
    for segment in segments:
        if isinstance(segment, Opaque) and segment.kind == AMPERSAND:
            unwrapped.append(Text(segment.source))
        elif isinstance(segment, Paired):
            unwrapped.append(
                Paired(segment.start, segment.end, _unwrap_ampersands(segment.children))
            )
        else:
            unwrapped.append(segment)
    return merge_text(unwrapped)


class HTMLGuard(Guard):
    """
    For services that translate HTML and leave elements with ``translate="no"``
    alone (Google Cloud Translation, Amazon Translate). Opaque segments are sent as
    ``<span translate="no" id="N">source</span>``, newlines as
    ``<br translate="no" id="N">`` and paired markup as ``<span id="N">...</span>``
    so the service can move it with the words it wraps. The service's copies of
    opaque text are ignored when decoding, the source is restored by id.

    Words in the text that contain ampersand sequences an HTML parser would decode
    (e.g. ``&copy`` or ``id=1&timestamp=2``, but not ``AT&T``) are also sent as
    ``translate="no"`` spans: Amazon Translate decodes entities in its input twice,
    so ``&amp;copy`` would come back as ``©``.
    """

    content_type = "html"

    def _encode_text(self, text: str, by_id: dict[str, Segment]) -> str:
        parts = []
        end = 0
        for match in _AMPERSAND_WORD.finditer(text):
            word = match.group(0)
            if html_lib.unescape(word) == word:
                continue
            parts.append(html_lib.escape(text[end : match.start()], quote=False))
            id_ = str(len(by_id))
            by_id[id_] = Opaque(word, AMPERSAND)
            source = html_lib.escape(word, quote=False)
            parts.append(f'<span translate="no" id="{id_}">{source}</span>')
            end = match.end()
        parts.append(html_lib.escape(text[end:], quote=False))
        return "".join(parts)

    def _encode(self, segments: list[Segment], by_id: dict[str, Segment]) -> str:
        parts = []
        for segment in segments:
            if isinstance(segment, Text):
                parts.append(self._encode_text(segment.text, by_id))
                continue
            id_ = str(len(by_id))
            by_id[id_] = segment
            if isinstance(segment, Paired):
                parts.append(
                    f'<span id="{id_}">{self._encode(segment.children, by_id)}</span>'
                )
            elif segment.kind == "newline":
                parts.append(f'<br translate="no" id="{id_}">')
            else:
                source = html_lib.escape(segment.source, quote=False)
                parts.append(f'<span translate="no" id="{id_}">{source}</span>')
        return "".join(parts)

    def encode(self, segments: list[Segment]) -> str:
        return self._encode(segments, {})

    def decode(self, translation: str, segments: list[Segment]) -> list[Segment] | None:
        by_id: dict[str, Segment] = {}
        self._encode(segments, by_id)
        decoder = _HTMLDecoder(by_id)
        decoded = decoder.feed(translation)
        if decoded is None:
            return None
        # protected ampersand words are text, but must not be lost in translation
        if any(
            id_ not in decoder.used
            for id_, segment in by_id.items()
            if isinstance(segment, Opaque) and segment.kind == AMPERSAND
        ):
            return None
        decoded = _unwrap_ampersands(decoded)
        if not same_opaques(segments, decoded):
            return None
        return decoded
