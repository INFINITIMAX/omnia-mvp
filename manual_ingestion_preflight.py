"""Preflight local, fără cost, pentru un singur PDF pus manual în inbox.

Modulul verifică un PDF și scrie numai un raport local minim. Nu importă date,
nu activează workerul istoric și nu contactează Supabase sau furnizori AI.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Callable, Mapping, Sequence

from procesare_documente import extrage_text


ROOT_PROIECT = Path(__file__).resolve().parent
FOLDER_INBOX = ROOT_PROIECT / "documente_noi" / "_inbox"
FOLDER_RAPOARTE = ROOT_PROIECT / "documente_noi" / "_reports"

# Aceste expresii identifică numai formele pe care le putem raporta fără ghicire.
# Orice lipsă sau mai multe rezultate oprește preflight-ul pentru verificare umană.
_PATTERN_COD = re.compile(
    r"(?im)^\s*((?:NP|P|I|C|NE|GP|GT|CR|STAS|SR(?:\s+EN(?:\s+ISO)?)?)\s*"
    r"\d+(?:\s*[./-]\s*\d+){0,3}(?:\s*[-/]\s*\d{4})?)\s*$"
)
_PATTERN_TITLU = re.compile(
    r"(?im)^\s*((?:NORMATIV(?:UL)?|REGLEMENTARE(?:A)?|GHID(?:UL)?|"
    r"INSTRUCȚIUNI(?:LE)?|INSTRUCTIUNI(?:LE)?|COD(?:UL)?|METODOLOGIA)\b[^\n]{12,500})\s*$"
)
_PATTERN_AN = re.compile(r"(?:^|[^0-9])(18[0-9]{2}|19[0-9]{2}|20[0-9]{2})(?:$|[^0-9])")
_PATTERN_ARTICOL = re.compile(
    r"\n\s*„?\s*(\d+\.\d+\.\s*\([A-Za-z]\)\.\s*(?:[IVXLl]\.|\d+\.)?(?:\d+\.)?|"
    r"ANEXA\s+\d+\.\d+\.|\d+\.\d+\.(?:\d+\.){0,4})"
)
_PATTERN_LINIE_CUPRINS = re.compile(r"\.{2,}\s*\d{1,4}\s*(?=\n|$)")
_PATTERN_SUBPUNCT = re.compile(r"\n\s*\((\d+)\)\s+")
_PATTERN_SPATIERE_ARTICOL = re.compile(r"[ \t\n\r\f\v\u00a0\u202f]+")
_PATTERN_ARTICOL_NORMALIZAT = re.compile(r"^[a-z0-9().-]+$")
_LUNGIME_MINIMA_CHUNK = 15
_LUNGIME_SPLIT_SECUNDAR = 2000


class PreflightError(ValueError):
    """Eroare controlată; mesajul este un token sigur pentru operatorul local."""


def _hash_sha256(cale: Path) -> str:
    """Citește PDF-ul în blocuri, astfel încât fișierele mari nu sunt încărcate complet."""
    digest = hashlib.sha256()
    try:
        with cale.open("rb") as fisier:
            for bloc in iter(lambda: fisier.read(1024 * 1024), b""):
                digest.update(bloc)
    except OSError as error:
        raise PreflightError("invalid_pdf_path") from error
    return digest.hexdigest()


def _cale_directa(cale: Path, director: Path, token: str, *, trebuie_sa_existe: bool) -> Path:
    """Acceptă doar un fișier direct sub directorul aprobat, inclusiv după resolve."""
    try:
        director_rezolvat = director.resolve()
        cale_rezolvata = cale.resolve()
    except OSError as error:
        raise PreflightError(token) from error

    if cale_rezolvata.parent != director_rezolvat:
        raise PreflightError(token)
    if trebuie_sa_existe and (not cale_rezolvata.is_file()):
        raise PreflightError(token)
    return cale_rezolvata


def _valideaza_pdf(cale_pdf: Path) -> Path:
    """Verifică poziția, existența și extensia înainte de extracție."""
    cale_pdf = _cale_directa(cale_pdf, FOLDER_INBOX, "outside_inbox", trebuie_sa_existe=True)
    if cale_pdf.suffix.casefold() != ".pdf":
        raise PreflightError("invalid_pdf_path")
    return cale_pdf


def _valideaza_raport(cale_raport: Path) -> Path:
    """Verifică locul raportului fără a crea fișiere pentru un PDF respins."""
    cale_raport = _cale_directa(cale_raport, FOLDER_RAPOARTE, "outside_reports", trebuie_sa_existe=False)
    if cale_raport.exists():
        raise PreflightError("report_exists")
    return cale_raport


def _normalizare_spatii(text: str) -> str:
    return " ".join(text.split())


def _unice(valori: Sequence[object]) -> tuple[object, ...]:
    """Păstrează ordinea și elimină duplicatele fără a transforma valori nehashable."""
    rezultat: list[object] = []
    for valoare in valori:
        if valoare not in rezultat:
            rezultat.append(valoare)
    return tuple(rezultat)


def find_metadata_candidates(text: str) -> dict[str, tuple[object, ...]]:
    """Extrage candidați, nu metadata finală; operatorul decide identitatea documentului."""
    if not isinstance(text, str):
        return {"cod_oficial": (), "titlu_oficial": (), "an": ()}

    coduri = _unice(tuple(_normalizare_spatii(match.group(1)) for match in _PATTERN_COD.finditer(text)))
    titluri = _unice(tuple(_normalizare_spatii(match.group(1)) for match in _PATTERN_TITLU.finditer(text)))
    ani = _unice(tuple(int(an) for cod in coduri for an in _PATTERN_AN.findall(str(cod))))
    return {"cod_oficial": coduri, "titlu_oficial": titluri, "an": ani}


def _metadata_unica(candidati: Mapping[str, Sequence[object]]) -> dict[str, object]:
    """Transformă câte un singur candidat în raport sau oprește în caz de ambiguitate."""
    try:
        coduri = tuple(candidati["cod_oficial"])
        titluri = tuple(candidati["titlu_oficial"])
        ani = tuple(candidati["an"])
    except (KeyError, TypeError) as error:
        raise PreflightError("ambiguous_metadata") from error

    if len(coduri) != 1 or len(titluri) != 1 or len(ani) != 1:
        raise PreflightError("ambiguous_metadata")
    if not isinstance(coduri[0], str) or not isinstance(titluri[0], str):
        raise PreflightError("ambiguous_metadata")
    if isinstance(ani[0], bool) or not isinstance(ani[0], int):
        raise PreflightError("ambiguous_metadata")
    return {"cod_oficial": coduri[0], "titlu_oficial": titluri[0], "an": ani[0]}


def _scrie_raport_atomic(cale_raport: Path, raport: Mapping[str, object]) -> None:
    """Rezervă numele cu O_EXCL și îl înlocuiește atomic numai cu JSON complet."""
    try:
        cale_raport.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(cale_raport, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as error:
        raise PreflightError("report_exists") from error
    except OSError as error:
        raise PreflightError("invalid_report_path") from error

    rezervat = True
    temporar = cale_raport.with_name(f".{cale_raport.name}.{uuid.uuid4().hex}.tmp")
    try:
        os.close(descriptor)
        with temporar.open("x", encoding="utf-8", newline="\n") as fisier:
            json.dump(raport, fisier, ensure_ascii=False, indent=2, sort_keys=True)
            fisier.write("\n")
            fisier.flush()
            os.fsync(fisier.fileno())
        os.replace(temporar, cale_raport)
        rezervat = False
    except OSError as error:
        raise PreflightError("report_write_failed") from error
    finally:
        try:
            temporar.unlink(missing_ok=True)
            if rezervat:
                cale_raport.unlink(missing_ok=True)
        except OSError:
            # Nu mascăm rezultatul valid sau eroarea inițială cu o problemă de cleanup.
            pass


def preflight_pdf(
    cale_pdf: Path,
    cale_raport: Path,
    *,
    extract_pdf: Callable[[Path], tuple[str, int]] = extrage_text,
    create_chunks: Callable[[str], Sequence[object]] | None = None,
    validate_chunks: Callable[[Sequence[object]], Sequence[object]] | None = None,
    find_metadata_candidates: Callable[[str], Mapping[str, Sequence[object]]] = find_metadata_candidates,
) -> dict[str, object]:
    """Verifică un PDF local și returnează exact conținutul raportului publicat local.

    Funcțiile de chunking sunt argumente pentru ca testele să rămână locale. Calea
    implicită aplică local reguli deterministe de separare pe articole, fără a
    persista chunk-uri sau a calcula embeddings.
    """
    pdf = _valideaza_pdf(Path(cale_pdf))
    raport = _valideaza_raport(Path(cale_raport))
    hash_inainte = _hash_sha256(pdf)

    try:
        text, pagini = extract_pdf(pdf)
    except Exception as error:
        hash_dupa_eroare = _hash_sha256(pdf)
        if hash_dupa_eroare != hash_inainte:
            raise PreflightError("unstable_pdf") from error
        raise PreflightError("invalid_extraction") from error

    if _hash_sha256(pdf) != hash_inainte:
        raise PreflightError("unstable_pdf")
    if not isinstance(text, str) or not text.strip() or isinstance(pagini, bool) or not isinstance(pagini, int) or pagini <= 0:
        raise PreflightError("invalid_extraction")

    if create_chunks is None:
        create_chunks = _creeaza_chunkuri_locale
    if validate_chunks is None:
        validate_chunks = _valideaza_chunkuri_locale
    try:
        chunkuri = create_chunks(text)
        chunkuri_validate = validate_chunks(chunkuri)
    except Exception as error:
        raise PreflightError("invalid_chunks") from error
    if not isinstance(chunkuri_validate, Sequence) or isinstance(chunkuri_validate, (str, bytes)) or not chunkuri_validate:
        raise PreflightError("invalid_chunks")

    metadata = _metadata_unica(find_metadata_candidates(text))
    rezultat: dict[str, object] = {
        "status": "ready_for_human_metadata",
        "source_sha256": hash_inainte,
        "page_count": pagini,
        "character_count": len(text),
        "chunk_count": len(chunkuri_validate),
        "metadata_candidates": metadata,
    }
    _scrie_raport_atomic(raport, rezultat)
    return rezultat


def _normalizeaza_articol(articol: object) -> str:
    """Aplică exact contractul ASCII al importerului înainte ca un chunk să fie valid.

    Spațiile dispar, literele devin mici și punctul final nu schimbă identitatea.
    Orice alt caracter este refuzat, nu eliminat sau interpretat.
    """
    if not isinstance(articol, str):
        raise ValueError("articol invalid")
    normalizat = _PATTERN_SPATIERE_ARTICOL.sub("", articol).lower().rstrip(".")
    if not _PATTERN_ARTICOL_NORMALIZAT.fullmatch(normalizat):
        raise ValueError("articol invalid")
    return normalizat


def _creeaza_chunkuri_locale(text: str) -> list[dict[str, str]]:
    """Aplică local chunking-ul determinist pe articole, fără DB sau embeddings.

    Este o copie restrânsă a regulii de structurare existente: sare peste un
    cuprins inițial, păstrează articolele cu text suficient și divide numai
    articolele foarte lungi după subpuncte. Rezultatul rămâne doar în memorie.
    """
    limita_cuprins = int(len(text) * 0.20)
    aparitii_cuprins = list(_PATTERN_LINIE_CUPRINS.finditer(text[:limita_cuprins]))
    continut = text[aparitii_cuprins[-1].end() :] if aparitii_cuprins else text
    sursa = "\n" + continut
    potriviri = list(_PATTERN_ARTICOL.finditer(sursa))
    dupa_articol: dict[str, dict[str, str]] = {}

    for index, potrivire in enumerate(potriviri):
        articol = potrivire.group(1).strip()
        # Dacă un caracter ne-separator urmează imediat identificatorului, îl
        # păstrăm pentru validator. Astfel `1.1./` nu devine tăcut `1.1.`.
        sufix = re.match(r"[^\s]+", sursa[potrivire.end(1) :])
        if sufix is not None:
            articol += sufix.group(0)
        inceput_text = potrivire.end()
        sfarsit_text = potriviri[index + 1].start() if index + 1 < len(potriviri) else len(sursa)
        text_articol = sursa[inceput_text:sfarsit_text].strip()
        if len(text_articol) < _LUNGIME_MINIMA_CHUNK:
            continue
        existent = dupa_articol.get(articol)
        if existent is None or len(text_articol) > len(existent["text"]):
            dupa_articol[articol] = {"articol": articol, "text": text_articol}

    rezultat: list[dict[str, str]] = []
    for chunk in dupa_articol.values():
        if len(chunk["text"]) < _LUNGIME_SPLIT_SECUNDAR:
            rezultat.append(chunk)
            continue
        subpuncte = _PATTERN_SUBPUNCT.split(chunk["text"])
        if len(subpuncte) == 1:
            rezultat.append(chunk)
            continue
        introducere = subpuncte[0].strip()
        if len(introducere) >= _LUNGIME_MINIMA_CHUNK:
            rezultat.append({"articol": chunk["articol"], "text": introducere})
        for index in range(1, len(subpuncte), 2):
            numar = subpuncte[index]
            text_subpunct = subpuncte[index + 1].strip() if index + 1 < len(subpuncte) else ""
            if len(text_subpunct) >= _LUNGIME_MINIMA_CHUNK:
                rezultat.append({"articol": f"{chunk['articol']}({numar})", "text": text_subpunct})
    return rezultat


def _valideaza_chunkuri_locale(chunkuri: Sequence[object]) -> Sequence[object]:
    """Refuză colecții goale sau fragmente care nu conțin text; nu persistă nimic."""
    if not isinstance(chunkuri, Sequence) or isinstance(chunkuri, (str, bytes)) or not chunkuri:
        raise ValueError("chunking invalid")
    for chunk in chunkuri:
        if not isinstance(chunk, Mapping) or not isinstance(chunk.get("text"), str) or not chunk["text"].strip():
            raise ValueError("chunk invalid")
        _normalizeaza_articol(chunk.get("articol"))
    return chunkuri


def main(argv: Sequence[str] | None = None) -> int:
    """Primește numai două căi explicite; nu scanează directoare și nu pornește importuri."""
    parser = argparse.ArgumentParser(description="Verifică local un singur PDF înainte de import.")
    parser.add_argument("--pdf", required=True, help="PDF direct din documente_noi/_inbox")
    parser.add_argument("--report", required=True, help="Raport JSON direct în documente_noi/_reports")
    arguments = parser.parse_args(argv)

    try:
        rezultat = preflight_pdf(Path(arguments.pdf), Path(arguments.report))
    except PreflightError as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps(rezultat, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
