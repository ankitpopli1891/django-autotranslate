set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]
set unstable
set script-interpreter := ['uv', 'run', '--project', '.', '--script']

export PYTHONPATH := source_directory()
export DJANGO_SETTINGS_MODULE := "tests.settings"

[private]
default:
    @just --list --list-submodules

# run the django admin
[script]
manage *COMMAND:
    import os
    import shlex
    from django.core import management
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")
    management.execute_from_command_line(["just manage", *shlex.split("{{ COMMAND }}")])

# machine translate this app's messages into all languages Django supports (paid google, set GOOGLE_TRANSLATE_API_KEY)
[positional-arguments]
[script]
translate *OPTS:
    import os
    import sys
    from pathlib import Path
    import django
    from django.conf import global_settings
    from django.core.management import call_command
    from django.utils.translation import to_locale
    # the justfile exports DJANGO_SETTINGS_MODULE for every recipe, so override it
    os.environ["DJANGO_SETTINGS_MODULE"] = "tests.translate"
    django.setup()
    # English is the source language
    locales = sorted({to_locale(code) for code, _ in global_settings.LANGUAGES if not code.startswith("en")})
    os.chdir(Path("src") / "autotranslate")
    Path("locale").mkdir(exist_ok=True)
    call_command("makemessages", locale=locales, no_obsolete=True, verbosity=0)
    # uses the service configured in tests/translate.py
    call_command("autotranslate", "--path", "locale", *sys.argv[1:])
    call_command("compilemessages", verbosity=0)

# install the uv package manager
[linux]
[macos]
install-uv:
    curl -LsSf https://astral.sh/uv/install.sh | sh

# install the uv package manager
[windows]
install-uv:
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# setup the venv and pre-commit hooks
setup python="python":
    uv venv -p {{ python }}
    @just install-prek

# install git pre-commit hooks
install-prek:
    uvx prek install

# update and install development dependencies
install *OPTS="--all-extras":
    uv sync {{ OPTS }}

_install-docs:
    uv sync --no-default-groups --group docs --all-extras

# run static type checking with mypy
check-types-mypy *ENV:
    @just run {{ ENV }} --no-default-groups --all-extras --group typing mypy

# run static type checking with pyright
check-types-pyright *ENV:
    @just run {{ ENV }} --no-default-groups --all-extras --group typing pyright

# run all static type checking
check-types *ENV:
    @just check-types-mypy {{ ENV }}
    @just check-types-pyright {{ ENV }}

# run all static type checking in an isolated environment
check-types-isolated *ENV:
    @just check-types-mypy {{ ENV }} --exact --isolated
    @just check-types-pyright {{ ENV }} --exact --isolated

# run package checks
check-package:
    uv pip check

# remove doc build artifacts
[script]
clean-docs:
    import shutil
    shutil.rmtree('./doc/build', ignore_errors=True)

# remove the virtual environment
clean-env:
    python -c "import shutil, pathlib; p=pathlib.Path('.venv'); shutil.rmtree(p, ignore_errors=True) if p.exists() else None"

# remove all git ignored files
clean-git-ignored:
    git clean -fdX

# remove all non-repository artifacts
clean: clean-docs clean-env clean-git-ignored

# build html documentation
build-docs-html:
    @just run --group docs --all-extras --isolated --no-default-groups --exact sphinx-build --fresh-env --builder html --doctree-dir ./doc/build/doctrees ./doc/source ./doc/build/html

# build the docs
build-docs: build-docs-html

# build docs and package
build: build-docs-html
    uv build

# open the html documentation
[script]
open-docs:
    import os
    import webbrowser
    webbrowser.open(f'file://{os.getcwd()}/doc/build/html/index.html')

# build and open the documentation
docs: build-docs-html open-docs

# serve the documentation with auto-reload
docs-live:
    @just run --group docs --all-extras --isolated --no-default-groups sphinx-autobuild doc/source doc/build --open-browser --watch src --port 0 --delay 1

_link-check:
    -uv run --no-default-groups --group docs sphinx-build -b linkcheck -Q -D linkcheck_timeout=10 ./doc/source ./doc/build

# check documentation links for broken links
[script]
check-docs-links: _link-check
    import os
    import sys
    import json
    from pathlib import Path
    data = json.loads(f"[{','.join((Path(os.getcwd()) / 'doc/build/output.json').read_text().splitlines())}]")
    broken_links = [
        link for link in data
        if link["status"] not in {"working", "redirected", "unchecked", "ignored"}
    ]
    if broken_links:
        for link in broken_links:
            print(f"[{link['status']}] {link['filename']}:{link['lineno']} -> {link['uri']}", file=sys.stderr)
        sys.exit(1)

# lint the documentation
check-docs *ENV:
    @just run {{ ENV }} --no-default-groups --group docs doc8 --ignore-path ./doc/build --max-line-length 100 -q ./doc

# fetch intersphinx references for the given package
[script]
fetch-refs LIB: _install-docs
    import os
    from pathlib import Path
    import logging as _logging
    import sys
    import runpy
    from sphinx.ext.intersphinx import inspect_main
    _logging.basicConfig()
    libs = runpy.run_path(Path(os.getcwd()) / "doc/source/conf.py").get("intersphinx_mapping")
    url = libs.get("{{ LIB }}", None)
    if not url:
        sys.exit(f"Unrecognized {{ LIB }}, must be one of: {', '.join(libs.keys())}")
    if url[1] is None:
        url = f"{url[0].rstrip('/')}/objects.inv"
    else:
        url = url[1]
    raise SystemExit(inspect_main([url]))

# lint the code
check-lint *ENV:
    @just run {{ ENV }} --no-default-groups --group lint ruff check --select I
    @just run {{ ENV }} --no-default-groups --group lint ruff check

# check if the code needs formatting
check-format *ENV:
    @just run {{ ENV }} --no-default-groups --group lint ruff format --check

# check that the readme renders
check-readme *ENV:
    @just run {{ ENV }} --no-default-groups --group lint -m readme_renderer ./README.md -o /tmp/README.html

# sort the python imports
sort-imports *ENV:
    @just run {{ ENV }} --no-default-groups --group lint ruff check --fix --select I

# format the code and sort imports
format *ENV:
    @just sort-imports {{ ENV }}
    just --fmt --unstable
    @just run {{ ENV }} --no-default-groups --group lint ruff format

# format the github workflow files
format-workflows:
    npx prettier --write ".github/workflows/*.{yml,yaml}"

# sort imports and fix linting issues
lint *ENV:
    @just sort-imports {{ ENV }}
    @just run {{ ENV }} --no-default-groups --group lint ruff check --fix

# fix formatting, linting issues and import sorting
fix *ENV:
    @just lint {{ ENV }}
    @just format {{ ENV }}

# run bandit static security analysis
bandit:
    @just run --no-default-groups --group lint bandit -c pyproject.toml -r ./src -f sarif -o bandit.sarif

# run zizmor security analysis of CI
zizmor:
    cargo install --locked zizmor
    zizmor --persona auditor --format sarif .github/workflows/ > zizmor.sarif

# run all static checks
check *ENV:
    @just check-lint {{ ENV }}
    @just check-format {{ ENV }}
    @just check-types {{ ENV }}
    @just check-package
    @just check-docs {{ ENV }}
    @just check-readme {{ ENV }}

# run all checks including documentation link checking (slow)
check-all *ENV:
    @just check {{ ENV }}
    @just check-docs-links

# run all tests (pass --group flags for db client and django version, e.g. --group psycopg3 --group dj52)
test-all *ENV:
    @just run {{ ENV }} --no-default-groups --exact --all-extras --group test --isolated pytest --cov-append

# run the live tests of a paid translation service (google or amazon) - these make billed requests
test-service SERVICE *ENV:
    @just run {{ ENV }} --no-default-groups --all-extras --group test pytest -m service tests/services/test_{{ SERVICE }}.py --no-cov

# run specific tests (project venv)
test *TESTS:
    @just run --group test --no-sync pytest {{ TESTS }}

# debug a test
debug-test *TESTS:
    @just run pytest \
      -o addopts='-ra -q' \
      -s --trace --pdbcls=IPython.terminal.debugger:Pdb \
      --headed {{ TESTS }}

# run the pre-commit checks
prek:
    uvx prek run

# erase any coverage data
coverage-erase:
    @just run --no-default-groups --group coverage coverage erase

# generate the test coverage report
coverage:
    @just run --no-default-groups --group coverage coverage combine --keep *.coverage
    @just run --no-default-groups --group coverage coverage report
    @just run --no-default-groups --group coverage coverage xml

# run the command in the virtual environment
run +ARGS:
    uv run {{ ARGS }}

# validate the given version string against the lib version
[script]
validate_version VERSION:
    import re
    import tomllib
    import autotranslate
    from packaging.version import Version
    raw_version = "{{ VERSION }}".lstrip("v")
    version_obj = Version(raw_version)
    assert str(version_obj) == raw_version
    assert raw_version == tomllib.load(open('pyproject.toml', 'rb'))['project']['version']
    assert raw_version == autotranslate.__version__
    print(raw_version)

# issue a release for the given semver string (e.g. 1.0.0)
release VERSION: install check-all
    @just validate_version v{{ VERSION }}
    git tag -s v{{ VERSION }} -m "{{ VERSION }} Release"
    git push https://github.com/ankitpopli1891/django-autotranslate.git v{{ VERSION }}
