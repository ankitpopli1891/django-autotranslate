.. include:: ../refs.rst

.. _howto-github-actions:

====================================
Automate translations with GitHub
====================================

This workflow runs ``autotranslate`` with Google Cloud Translation when you start it,
and opens a pull request with the new translations. The API key is kept in a GitHub
environment that you approve each run of, so nobody can spend money on your account
without you knowing.

Set up the environment
======================

#. In your repository's *Settings → Environments*, create an environment named
   ``translate``.
#. Add yourself under **Required reviewers**.
#. Add an environment secret ``GOOGLE_TRANSLATE_API_KEY`` with your key (see
   :ref:`howto-google-cloud`).
#. In *Settings → Actions → General → Workflow permissions*, enable **Allow GitHub
   Actions to create and approve pull requests**.

Your settings must read the key from the ``GOOGLE_TRANSLATE_API_KEY`` environment
variable, as shown in :ref:`howto-google-cloud`.

Add the workflow
================

Create ``.github/workflows/translate.yml``:

.. code-block:: yaml

    name: Translate

    on:
      workflow_dispatch:

    permissions:
      contents: read

    jobs:
      translate:
        runs-on: ubuntu-latest
        environment: translate
        permissions:
          contents: write
          pull-requests: write
        steps:
          - uses: actions/checkout@v4
            with:
              persist-credentials: false
          - uses: actions/setup-python@v5
            with:
              python-version: "3.13"
          - name: Install gettext
            run: sudo apt-get install -y gettext
          - name: Install dependencies
            run: pip install -r requirements.txt "django-autotranslate[google]"
          - name: Translate
            env:
              GOOGLE_TRANSLATE_API_KEY: ${{ secrets.GOOGLE_TRANSLATE_API_KEY }}
              DJANGO_SETTINGS_MODULE: mysite.settings
              PYTHONPATH: .
            run: |
              django-admin makemessages --all
              django-admin autotranslate --no-progress
              django-admin compilemessages
          - uses: peter-evans/create-pull-request@v7
            with:
              branch: update-translations
              add-paths: locale
              title: Update translations
              commit-message: Update machine translations
              body: Machine translations from autotranslate. Please review before merging.

Adjust the install step and ``add-paths`` for your project. Pin the actions to commit
SHAs if your security policy requires it.

Run it
======

Start it from *Actions → Translate → Run workflow*. The run waits for your approval,
then opens or updates a pull request on the ``update-translations`` branch.

Pull requests opened with the workflow's token do not start other workflows, so your
tests do not run on it automatically. Close and reopen the pull request, or push to its
branch, to run them.
