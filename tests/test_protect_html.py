import random
import time

import pytest

from autotranslate.protect.html import html
from autotranslate.protect.parse import parse
from autotranslate.protect.segments import (
    Opaque,
    Paired,
    Text,
    opaques,
    flatten,
    serialize,
)


def test_not_html():
    assert html("a < b > c & d") == [Text("a < b > c & d")]


def test_paired_and_void():
    assert html('Read <a href="/x">the docs</a><br/>') == [
        Text("Read "),
        Paired(
            Opaque('<a href="/x">', "tag", "a"),
            Opaque("</a>", "tag", "a"),
            [Text("the docs")],
        ),
        Opaque("<br/>", "tag", "br"),
    ]


def test_opaque_elements_and_entities():
    assert html("Run <code>make <b>x</b></code> &nbsp; &#39;") == [
        Text("Run "),
        Opaque("<code>make <b>x</b></code>", "tag", "code"),
        Text(" "),
        Opaque("&nbsp;", "entity"),
        Text(" "),
        Opaque("&#39;", "entity"),
    ]


@pytest.mark.parametrize(
    "text",
    [
        "<CODE>x</CODE> and </A >",
        "<b>a <i>b</b> c",
        "<b>unclosed and </i> stray",
        "<br> then <b>bold</b>",
        "<!-- note --> text",
        '<a href="%(url)s">docs</a>\nnext',
    ],
)
def test_round_trip(text):
    assert serialize(html(text)) == text
    assert serialize(parse(text, ["python-format"])) == text


def test_parse_composes_tokenizers():
    assert parse('<a href="%(url)s">Hi %(name)s</a>\nok', ["python-format"]) == [
        Paired(
            Opaque('<a href="%(url)s">', "tag", "a"),
            Opaque("</a>", "tag", "a"),
            [Text("Hi "), Opaque("%(name)s", "printf", "name")],
        ),
        Opaque("\n", "newline"),
        Text("ok"),
    ]


@pytest.mark.parametrize(
    "text",
    [
        "<b>AT&T</b> R&D, M&S",
        "Ask <b>Q&A</b> now",
        "Fish &chips <i>x</i>",
        "<i>x</i> &amp",
    ],
)
def test_bare_ampersands_stay_text(text):
    segments = html(text)
    assert serialize(segments) == text
    assert not [s for s in opaques(segments) if s.kind == "entity"]
    assert "&" in "".join(s.text for s in flatten(segments) if isinstance(s, Text))


@pytest.mark.parametrize("text", ["<!DOCTYPE x>", "<?pi?>", "<![CDATA[c]]>", "<!x>"])
def test_declarations(text):
    assert html(text) == [Opaque(text, "declaration")]


@pytest.mark.parametrize(
    "text",
    [
        "</ x>",
        "</>",
        "<b>x</b><a",
        "<!-- x <b>y</b>",
        "<script>x",
        "a < b > c <",
    ],
)
def test_malformed_round_trip(text):
    assert serialize(html(text)) == text


def test_attribute_with_angle_bracket():
    assert html("<a title='a>b'>x</a>") == [
        Paired(
            Opaque("<a title='a>b'>", "tag", "a"),
            Opaque("</a>", "tag", "a"),
            [Text("x")],
        )
    ]


def test_nested_opaque_elements():
    assert html("<code><var>x</var></code>") == [
        Opaque("<code><var>x</var></code>", "tag", "code")
    ]


def test_void_elements_do_not_swallow():
    assert html('<br>a<img src="x">b') == [
        Opaque("<br>", "tag", "br"),
        Text("a"),
        Opaque('<img src="x">', "tag", "img"),
        Text("b"),
    ]


def test_random_round_trip():
    atoms = [
        "<b>", "</b>", "<I class='x>y'>", "</I >", "<A HREF=\"u\">", "</a>",
        "<br>", "<br/>", "<code>", "</code>", "<script>", "&amp;", "&amp", "&#39;",
        "&#x27;", "&", "<", ">", "<!-- c -->", "<!--", "<!DOCTYPE x>", "<?pi?>",
        "<![CDATA[c]]>", "%(n)s", "%s", "{x}", "{", "}", "word", "AT&T", " ", "\n",
        "</", "<a", "'", '"', "=",
    ]  # fmt: skip
    rng = random.Random(1234)
    for _ in range(2000):
        text = "".join(rng.choice(atoms) for _ in range(rng.randint(1, 12)))
        flags = ["python-format", "python-brace-format"]
        assert serialize(html(text)) == text
        assert serialize(parse(text, flags)) == text


def test_quote_with_angle_bracket_only_markup():
    assert html("\n<a title='<'>") == [
        Text("\n"),
        Opaque("<a title='<'>", "tag", "a"),
    ]


def test_no_quadratic_lexing():
    text = "<b>" + "<a " * 5000
    start = time.perf_counter()
    assert serialize(html(text)) == text
    assert time.perf_counter() - start < 1.0


def test_deep_nesting_falls_back_to_text():
    text = "<b>" * 3000 + "</b>" * 3000
    assert html(text) == [Text(text)]


def test_flatten():
    segments = html("a <b>c <i>d</i></b> e")
    flat = flatten(segments)
    assert not any(isinstance(s, Paired) for s in flat)
    assert serialize(flat) == serialize(segments)
    assert [s.source for s in flat if isinstance(s, Opaque)] == [
        "<b>",
        "<i>",
        "</i>",
        "</b>",
    ]


@pytest.mark.parametrize("text", [" ", "\n", " \n "])
def test_match_edges_whitespace_only(text):
    from autotranslate.protect.repair import match_edges

    assert match_edges(text, text) == text
