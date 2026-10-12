"""
The translations in these tests are real outputs from Google Cloud Translation for
the encoded messages.
"""

import re

import pytest

from autotranslate.protect.guards import HTMLGuard, TokenGuard
from autotranslate.protect.pipeline import protect, restore


def span(id_, text):
    return f'<span translate="no" id="{id_}">{text}</span>'


HTML = HTMLGuard()
TOKEN = TokenGuard()


def test_html_encode():
    protected = protect(
        'Read the <a href="%(url)s">docs</a> & %(n)d\nnow', HTML, ["python-format"]
    )
    assert protected.encoded == (
        'Read the <span id="0">docs</span> &amp; '
        '<span translate="no" id="1">%(n)d</span><br translate="no" id="2">now'
    )


def test_token_encode():
    assert (
        protect("100%% of %(n)d", TOKEN, ["python-format"]).encoded
        == "100__x0__ of __x1__"
    )
    assert (
        protect("Saved %s %s", TOKEN, ["python-format"]).encoded
        == "Saved __x0__ __x1__"
    )


@pytest.mark.parametrize(
    "source, flags, translation, expected",
    [
        ("Saved %s", ["python-format"], "Salvo " + span(0, "%s"), "Salvo %s"),
        # a space dropped between a word and a placeholder is restored
        (
            "Saved %s",
            ["python-format"],
            'Salvo<span translate="no" id="0"></span>',
            "Salvo %s",
        ),
        # spaces added between placeholders and punctuation are removed
        (
            "Skipping {file}: {service} does not support `{language}`",
            ["python-brace-format"],
            f"Bỏ qua {span(0, '{file}')} : {span(1, '{service}')} không hỗ trợ ` {span(2, '{language}')} `",
            "Bỏ qua {file}: {service} không hỗ trợ `{language}`",
        ),
        (
            "`{service}` requires the `{package}` package.",
            ["python-brace-format"],
            f"` {span(0, '{service}')} ` ئۈچۈن ` {span(1, '{package}')} ` پاكېت تەلەپ قىلىنىدۇ.",
            "`{service}` ئۈچۈن `{package}` پاكېت تەلەپ قىلىنىدۇ.",
        ),
        (
            "Hello %(name)s, you have %(count)d new messages.",
            ["python-format"],
            f"Hallo {span(0, '%(name)s')} , du hast {span(1, '%(count)d')} neue Nachrichten.",
            "Hallo %(name)s, du hast %(count)d neue Nachrichten.",
        ),
        # no spaces are added in scripts written without them
        (
            "Hello %(name)s, you have %(count)d new messages.",
            ["python-format"],
            f"こんにちは{span(0, '%(name)s')} 。 {span(1, '%(count)d')}新しいメッセージが届きました。",
            "こんにちは%(name)s。 %(count)d新しいメッセージが届きました。",
        ),
        # newlines survive and the space added after them is removed
        (
            "First line\nSecond line",
            [],
            'Erste Zeile<br translate="no" id="0"> Zweite Zeile',
            "Erste Zeile\nZweite Zeile",
        ),
        (
            "Line one \n  indented",
            [],
            'Zeile eins <br translate="no" id="0">  eingerückt',
            "Zeile eins \n  eingerückt",
        ),
        # paired markup is restored around its translated content
        (
            'Read the <a href="%(url)s">docs</a> & more',
            ["python-format"],
            'Lesen Sie die <span id="0">Dokumentation</span> &amp; mehr',
            'Lesen Sie die <a href="%(url)s">Dokumentation</a> & mehr',
        ),
        (
            "<b>Hello <i>%(name)s</i></b>!",
            ["python-format"],
            '<span id="0">Hallo <span id="1"><span translate="no" id="2">%(name)s</span></span></span> !',
            "<b>Hallo <i>%(name)s</i></b>!",
        ),
        # the service's escaping is undone
        ("Fish & 'chips'", [], "Fisch &amp; &#39;Pommes&#39;", "Fisch & 'Pommes'"),
        # markup added by the service is dropped
        (
            "Saved %s",
            ["python-format"],
            '<span class="x">Salvo</span> ' + span(0, "%s"),
            "Salvo %s",
        ),
        # the source is restored, not the service's copy
        (
            "Saved %(n)s",
            ["python-format"],
            "Salvo " + span(0, "%(nome)s"),
            "Salvo %(n)s",
        ),
        # lost and duplicated placeholders are rejected
        ("Saved %s", ["python-format"], "Salvo item", None),
        ("Saved %s", ["python-format"], f"Salvo {span(0, '%s')} {span(0, '%s')}", None),
    ],
)
def test_html_guard(source, flags, translation, expected):
    assert restore(protect(source, HTML, flags), translation) == expected


@pytest.mark.parametrize(
    "source, flags, translation, expected",
    [
        ("Saved %s", ["python-format"], "Gespeichert __x0__", "Gespeichert %s"),
        # Google translated the token as a word
        ("Saved %s", ["python-format"], "Item salvo", None),
        # named tokens are restored by name
        ("%(a)s and %(b)s", ["python-format"], "__x1__ y __x0__", "%(b)s y %(a)s"),
        (
            "100%% of %(n)d",
            ["python-format"],
            "100__x0__ von __x1__",
            "100%% von %(n)d",
        ),
        # leading and trailing whitespace comes from the source
        ("\nLeading newline", [], "Führende Zeile", "\nFührende Zeile"),
        # a mangled token is rejected
        ("`{package}` package", ["python-brace-format"], "`__ paket__` bolaq", None),
    ],
)
def test_token_guard(source, flags, translation, expected):
    assert restore(protect(source, TOKEN, flags), translation) == expected


@pytest.mark.parametrize(
    "source, flags, translation, expected",
    [
        # raw angle brackets and ampersands in service text are text
        (
            "Is %s ok",
            ["python-format"],
            f"{span(0, '%s')} ok 1<2 and a<b & c",
            "%s ok 1<2 and a<b & c",
        ),
        ("Saved %s", ["python-format"], f"fim <a {span(0, '%s')}", "fim <a %s"),
        ("Saved %s", ["python-format"], f"&lt;b&gt; {span(0, '%s')}", None),
        ("Saved %s", ["python-format"], f"&lt;3 {span(0, '%s')}", "<3 %s"),
        # single quoted, unquoted and upper case markup
        ("Saved %s", ["python-format"], "Salvo <SPAN ID='0'>x</SPAN>", "Salvo %s"),
        ("Saved %s", ["python-format"], "Salvo <span id=0>x</span>", "Salvo %s"),
        # comments and declarations are dropped
        ("Saved %s", ["python-format"], f"<!-- c -->Salvo {span(0, '%s')}", "Salvo %s"),
        # unknown tags are dropped, their text kept
        (
            "Saved %s",
            ["python-format"],
            f"Salvo<br> <b>muito</b><img src='a'><hr/> {span(0, '%s')}",
            "Salvo muito %s",
        ),
        # lost, duplicated and unclosed spans are rejected
        ("Saved %s", ["python-format"], "Salvo", None),
        ("Saved %s", ["python-format"], f"{span(0, '%s')}{span(0, '%s')}", None),
        ("Saved %s", ["python-format"], '<span id="0">%s', None),
        # paired ids on void elements must not inject the source's children
        ('Read <a href="x">docs</a>', [], 'Lê <span id="0"/> agora', None),
        ('Read <a href="x">docs</a>', [], 'Lê <br id="0"> agora', None),
        ("Saved %s", ["python-format"], 'Lê <br id="0"> agora', None),
        ("Saved %s", ["python-format"], 'Lê <span id="0"/> agora', "Lê %s agora"),
        ("a\nb", [], 'a<br translate="no" id="0">b', "a\nb"),
    ],
)
def test_html_decode_hardening(source, flags, translation, expected):
    assert restore(protect(source, HTML, flags), translation) == expected


@pytest.mark.parametrize(
    "source, flags, translation, expected",
    [
        # a duplicated token is rejected
        ("a %(n)d", ["python-format"], "a __n__ __n__", None),
        # unknown literal tokens are kept
        ("a %(n)d", ["python-format"], "a __word__ __x0__", "a __word__ %(n)d"),
        # literal tokens in the source do not collide with real ones
        ("__item__ %s", ["python-format"], "__item__ __x0__", "__item__ %s"),
        ("__item__ %s", ["python-format"], "__item__ __item__", None),
    ],
)
def test_token_guard_hardening(source, flags, translation, expected):
    assert restore(protect(source, TOKEN, flags), translation) == expected


def test_token_markup_does_not_collide_with_placeholder():
    protected = protect("%(x0)s <b>bold</b>", TOKEN, ["python-format"])
    encoded = protected.encoded
    names = re.findall(r"__(\w+?)__", encoded)
    assert len(names) == 3 and len(set(names)) == 3
    first, start, end = names
    translated = f"__{start}__negrito__{end}__ __{first}__"
    assert restore(protected, translated) == "<b>negrito</b> %(x0)s"


NBSP = "\u00a0"


@pytest.mark.parametrize(
    "source, flags, translation, expected",
    [
        ("%s%s", ["python-format"], f"{span(0, '%s')} {span(1, '%s')}", "%s%s"),
        ("%s %s", ["python-format"], f"{span(0, '%s')} {span(1, '%s')}", "%s %s"),
        # French typography is kept, ordinary spaces are removed
        (
            "{file}: x",
            ["python-brace-format"],
            f"{span(0, '{file}')}{NBSP}: x",
            f"{{file}}{NBSP}: x",
        ),
        ("{file}: x", ["python-brace-format"], f"{span(0, '{file}')} : x", "{file}: x"),
        (
            "\u00ab %s \u00bb",
            ["python-format"],
            f"\u00ab{NBSP}{span(0, '%s')}{NBSP}\u00bb",
            f"\u00ab{NBSP}%s{NBSP}\u00bb",
        ),
        (
            "`%s` x",
            ["python-format"],
            f"`{NBSP}{span(0, '%s')}{NBSP}` x",
            f"`{NBSP}%s{NBSP}` x",
        ),
    ],
)
def test_repair_whitespace(source, flags, translation, expected):
    assert restore(protect(source, HTML, flags), translation) == expected


@pytest.mark.parametrize(
    "source, flags, translation",
    [
        ("{file}: x", ["python-brace-format"], f"{span(0, '{file}')} : x"),
        ("Saved %s", ["python-format"], f"Salvo{span(0, '%s')}"),
        ("%s%s", ["python-format"], f"{span(0, '%s')} {span(1, '%s')}"),
        ("`%s` x", ["python-format"], f"` {span(0, '%s')} ` x"),
    ],
)
def test_repair_idempotent(source, flags, translation):
    from autotranslate.protect.parse import parse
    from autotranslate.protect.repair import repair

    segments = parse(source, flags)
    decoded = HTML.decode(translation, segments)
    once = repair(segments, decoded)
    assert repair(segments, once) == once


@pytest.mark.parametrize(
    "guard, translation",
    [
        # the service added placeholders or markup outside the guards
        (HTML, f"Salvo {span(0, '%s')} (%s)"),
        (HTML, f"Salvo {span(0, '%s')} &lt;b&gt;"),
        (TOKEN, "Salvo __item__ %d"),
    ],
)
def test_restore_rejects_extra_directives(guard, translation):
    protected = protect("Saved %s", guard, ["python-format"])
    assert restore(protected, translation) is None


def test_repair_respects_reordering():
    protected = protect("%(a)s%(b)s and %(c)s", TOKEN, ["python-format"])
    # a, b and c are __x0__, __x1__ and __x2__
    out = restore(protected, "__x0__ __x2__ e __x1__")
    assert out == "%(a)s %(c)s e %(b)s"
    assert restore(protected, "__x0____x1__ e __x2__") == "%(a)s%(b)s e %(c)s"


@pytest.mark.parametrize(
    "source, translation, expected",
    [
        # end before start
        ("<b>Hello</b> world", "__x1__Hello__x0__ world", None),
        # crossed nesting
        ("<b><i>Hi</i></b>", "__x0____x1__Hi__x3____x2__", None),
        # well formed, reordered
        ("<b>Hello</b> world", "mundo __x0__Hola__x1__", "mundo <b>Hola</b>"),
        ("<b><i>Hi</i></b>", "__x0____x1__Hola__x2____x3__", "<b><i>Hola</i></b>"),
    ],
)
def test_token_guard_markup_structure(source, translation, expected):
    assert restore(protect(source, TOKEN), translation) == expected


def test_token_guard_unclosed_markup():
    assert restore(protect("<b>Hello</b>", TOKEN), "__x0__Hola") is None


def test_token_guard_positional_fields_keep_identity():
    protected = protect("{0} of {1}", TOKEN, ["python-brace-format"])
    assert protected.encoded == "__x0__ of __x1__"
    assert restore(protected, "__x1__的__x0__") == "{1}的{0}"


def test_token_guard_attribute_fields_keep_identity():
    protected = protect("{user.first} {user.last}", TOKEN, ["python-brace-format"])
    names = re.findall(r"__(\w+?)__", protected.encoded)
    assert len(names) == 2 and len(set(names)) == 2
    assert (
        restore(protected, f"__{names[1]}__, __{names[0]}__")
        == "{user.last}, {user.first}"
    )


def test_token_guard_numbers_every_placeholder():
    # numbered tokens, not names, which services translate as words
    protected = protect("{service}: {name} {name}", TOKEN, ["python-brace-format"])
    assert protected.encoded == "__x0__: __x1__ __x2__"
    assert restore(protected, "__x2__ __x1__: __x0__") == "{name} {name}: {service}"


@pytest.mark.parametrize("source", ["%(a__b)s", "%(name_)s", "%(_x)s"])
def test_token_guard_unnameable_placeholders_round_trip(source):
    protected = protect(f"Hi {source}!", TOKEN, ["python-format"])
    assert restore(protected, protected.encoded) == f"Hi {source}!"


@pytest.mark.parametrize("guard", [HTML, TOKEN])
@pytest.mark.parametrize(
    "source, flags",
    [
        ("Total:\n%(n)s", ["python-format"]),
        ("Hello,\n%s", ["python-format"]),
        ("%s\n:", ["python-format"]),
        ("Files:\n{count}", ["python-brace-format"]),
        ("Name:\n<b>x</b>", []),
    ],
)
def test_newline_next_to_punctuation_survives(guard, source, flags):
    protected = protect(source, guard, flags)
    assert restore(protected, protected.encoded) == source


def test_token_numbering_is_deterministic():
    import os
    import subprocess
    import sys

    code = (
        "from autotranslate.protect.guards import TokenGuard;"
        "from autotranslate.protect.pipeline import protect;"
        "print(protect('{0} and {0:>5} and {1!r} {1} {2} {3}', TokenGuard(),"
        " ['python-brace-format']).encoded)"
    )
    outputs = {
        subprocess.run(
            [sys.executable, "-c", code],
            env={**os.environ, "PYTHONHASHSEED": seed},
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        for seed in ("1", "2", "3", "4")
    }
    assert len(outputs) == 1


def test_restore_rejects_regrouped_loose_tags():
    protected = protect("</I >%(n)s%d</a><I class='x>y'>", TOKEN, ["python-format"])
    tokens = re.findall(r"__\w+?__", protected.encoded)
    assert len(tokens) == 5
    first, n, d, end_a, start_i = tokens
    assert restore(protected, "".join(tokens)) is not None
    # the loose tags regrouped into a new element
    assert restore(protected, "".join([end_a, start_i, first, n, d])) is None


def test_restore_keeps_paired_markup():
    protected = protect("Read <a href='/x'>docs</a>", TOKEN)
    assert restore(protected, "Lea __x0__docs__x1__") == "Lea <a href='/x'>docs</a>"


def test_paragraph_break_from_html_service():
    protected = protect("Para one.\n\nPara two.", HTML)
    translation = (
        'Absatz eins.<br translate="no" id="0"> <br translate="no" id="1"> Absatz zwei.'
    )
    assert restore(protected, translation) == "Absatz eins.\n\nAbsatz zwei."


@pytest.mark.parametrize("guard", [HTML, TOKEN])
def test_paragraph_break_round_trips(guard):
    protected = protect("Para one.\n\nPara two.", guard)
    assert restore(protected, protected.encoded) == "Para one.\n\nPara two."


# Amazon decodes entities in its input twice, so "&amp;copy" comes back as "©".
# Words containing ampersand sequences that would decode as an entity are sent as
# do-not-translate spans.


@pytest.mark.parametrize(
    "source, translation, expected",
    [
        (
            "See &copy and id=1&timestamp=2 now",
            'Siehe jetzt <span translate="no" id="0">&amp;copy</span> und '
            '<span translate="no" id="1">id=1&amp;timestamp=2</span>',
            "Siehe jetzt &copy und id=1&timestamp=2",
        ),
        # the service's copy of a protected word is ignored
        (
            "See &copy now",
            'Siehe jetzt <span translate="no" id="0">©</span>',
            "Siehe jetzt &copy",
        ),
        # a lost protected word is rejected
        ("See &copy now", "Siehe jetzt ©", None),
        # ampersands that don't decode are translated as text
        ("AT&T and R&D", "AT&T und R&D", "AT&T und R&D"),
    ],
)
def test_html_guard_ampersands(source, translation, expected):
    assert restore(protect(source, HTML, []), translation) == expected


def test_html_guard_ampersand_encoding():
    assert protect("AT&T and &copy", HTML, []).encoded == (
        'AT&amp;T and <span translate="no" id="0">&amp;copy</span>'
    )


@pytest.mark.parametrize(
    "source, flags, translation, expected",
    [
        # Amazon: the space before an opening quote is kept
        (
            "Fish & chips are 'ready' at 100%%.",
            ["python-format"],
            'Fish & Chips sind bei 100 <span translate="no" id="0">%%</span> „fertig“.',
            "Fish & Chips sind bei 100 %% „fertig“.",
        ),
        (
            "Fish & chips are 'ready' at 100%%.",
            ["python-format"],
            '炸鱼薯条在 100 <span translate="no" id="0">%%</span> “准备就绪” 了。',
            "炸鱼薯条在 100 %% “准备就绪” 了。",
        ),
        # brackets attach to placeholders
        (
            "(%s)",
            ["python-format"],
            '( <span translate="no" id="0">%s</span> )',
            "(%s)",
        ),
        # the same quote character the source had attaches
        (
            "'%s'",
            ["python-format"],
            '\' <span translate="no" id="0">%s</span> \'',
            "'%s'",
        ),
    ],
)
def test_repair_quotes(source, flags, translation, expected):
    assert restore(protect(source, HTML, flags), translation) == expected
