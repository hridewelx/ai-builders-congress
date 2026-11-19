"""The page behaviour is split into small files; base.html must load all of them.

A missing <script> tag would leave a page silently dead, so the wiring is
checked rather than assumed.
"""
from __future__ import annotations

import re
from pathlib import Path

BASE = Path("templates/base.html").read_text(encoding="utf-8")
SCRIPTS = sorted(Path("static/js").glob("*.js"))


def test_every_behaviour_file_is_loaded_by_the_page():
    assert SCRIPTS, "no behaviour files found"
    for script in SCRIPTS:
        assert f'/static/js/{script.name}"' in BASE, f"{script.name} is not loaded"


def test_the_shared_runner_is_loaded_last():
    order = re.findall(r'<script src="/static/(?:js/)?([^"]+)\.js"', BASE)
    assert order, "no scripts wired"
    assert order[-1] == "app", "app.js must run after the behaviour files"
    assert "js/" not in order[-2], "the behaviour files must come before app.js"


def test_behaviour_files_only_register_a_boot_function():
    for script in SCRIPTS:
        text = script.read_text(encoding="utf-8")
        assert "window.LotlineBoot = window.LotlineBoot || [];" in text, script.name
        assert "window.LotlineBoot.push(function (api) {" in text, script.name
        assert '"use strict"' in text, script.name
        assert "eval(" not in text, script.name
