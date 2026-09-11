"""Simulare de provider doar pentru regresiile vechi, niciodată fallback runtime.

Cazurile R06 și cazurile structurale invalide folosesc RawGeneratorFake sau propriul
RAW; helperul de împachetare nu este folosit pentru evaluator și nu primește gold.
"""

import json
import re
from dataclasses import dataclass

from generation_core import GeneratedText


def simulated_provider_payload(candidate: str | GeneratedText, prompt: str) -> str | GeneratedText:
    """Simulează alegerea prefixului sintetic de către provider pentru teste vechi.

    Nu repară ID-uri sau text. Alegerea pasajului relevant/tardiv este testată
    separat prin payloaduri RAW explicite, fără ajutorul acestei simulări.
    """
    answer = candidate.text if isinstance(candidate, GeneratedText) else candidate
    documents = json.loads(prompt.split("<dovezi_json>\n", 1)[1].split("\n</dovezi_json>", 1)[0])
    by_id = {item["id_citare"]: item["text"] for item in documents}
    ids = tuple(dict.fromkeys(value.upper() for value in re.findall(r"\[([Cc][1-9][0-9]*)\]", answer)))
    # O fixture invalidă trebuie aleasă explicit RAW, nu corectată de helper.
    assert answer.strip() and ids and all(value in by_id for value in ids)
    payload = json.dumps({
        "raspuns": answer,
        "pasaje": [{"id": value, "citat": by_id[value][:600]} for value in ids],
    }, ensure_ascii=False)
    if isinstance(candidate, GeneratedText):
        return GeneratedText(payload, truncated=candidate.truncated)
    return payload


@dataclass
class RawGeneratorFake:
    """Transport literal pentru payloaduri alese explicit, inclusiv cele invalide."""

    answer: str | GeneratedText
    calls: int = 0
    prompt: str | None = None
    max_tokens: int | None = None

    def generate(self, prompt, *, max_tokens):
        self.calls += 1
        self.prompt = prompt
        self.max_tokens = max_tokens
        return self.answer
