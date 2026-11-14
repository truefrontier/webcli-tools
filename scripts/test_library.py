"""library.py's own tests: `python scripts/library.py check` runs them when pytest is installed."""

from __future__ import annotations

from library import keeps_verified

NEW = {"name": "acmenotes", "version": "0.1.0", "sha256": "a" * 64}  # what `pin` is about to write
OLD = {**NEW, "verified": True}  # the entry it replaces, which a maintainer verified


def test_same_version_with_changed_files_is_not_verified():
    assert keeps_verified(OLD, {**NEW, "sha256": "b" * 64}) is False


def test_the_same_files_stay_verified():
    assert keeps_verified(OLD, NEW) is True


def test_a_new_version_is_not_verified():
    assert keeps_verified(OLD, {**NEW, "version": "0.2.0", "sha256": "b" * 64}) is False
