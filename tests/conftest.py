"""Gărzi globale pentru suita de teste."""

import pytest


@pytest.fixture(autouse=True)
def _fara_apeluri_platite_la_anthropic(monkeypatch):
    """`main.py` încarcă `.env` la import, deci în folderul principal cheia Anthropic reală
    există în mediu. Fără gardă, orice test care ajunge pe ruta semantică cu rescrierea
    implicită (R30) ar chema Claude Haiku real: cost, rețea și rezultate instabile.
    Testele care au nevoie de cheie o setează explicit, cu o valoare falsă."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
