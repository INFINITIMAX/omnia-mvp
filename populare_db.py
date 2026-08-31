"""Importa documentele structurate din documente_noi in Supabase.

Pentru fiecare document, scriptul citeste metadata.json + extracted.txt, creeaza
chunk-uri si reinlocuieste numai chunk-urile acelei surse. Nu mai goleste tabelul
complet. Foloseste --dry-run pentru validare fara DB, Voyage sau costuri API.
"""

import argparse
import glob
import json
import os
import re
from pathlib import Path

import psycopg2
import voyageai
from dotenv import load_dotenv

ROOT_PROIECT = Path(__file__).resolve().parent
FOLDER_DOCUMENTE = ROOT_PROIECT / "documente_noi"

# Regex-ul actual pentru structura articolelor din normativele deja validate.
PATTERN_ARTICOL = re.compile(
    r"\n\s*(\d+\.\d+\.\s*\([A-Za-z]\)\.\s*(?:[IVXLl]\.|\d+\.)?(?:\d+\.)?|ANEXA\s+\d+\.\d+\.|\d+\.\d+\.(?:\d+\.){0,4})"
)
PATTERN_LINIE_CUPRINS = re.compile(r"\.{2,}\s*\d{1,4}\s*(?=\n|$)")
PATTERN_SUBPUNCT = re.compile(r"\n\s*\((\d+)\)\s+")
PROCENT_MAXIM_CAUTARE_CUPRINS = 0.20
LUNGIME_MINIMA_CHUNK = 15
LUNGIME_PENTRU_SPLIT_SECUNDAR = 2000


def gaseste_documente():
    """Cauta documente cu metadata si text extras, ignorand _inbox/_rejected."""
    for folder in sorted(FOLDER_DOCUMENTE.iterdir()):
        if not folder.is_dir() or folder.name.startswith("_"):
            continue

        cale_metadata = folder / "metadata.json"
        cale_text = folder / "extracted.txt"
        if not cale_metadata.exists() or not cale_text.exists():
            print(f"  SARIT: {folder.name} — necesita metadata.json si extracted.txt")
            continue

        try:
            metadata = json.loads(cale_metadata.read_text(encoding="utf-8-sig"))
            if not metadata.get("document_id") or not metadata.get("source_key"):
                raise ValueError("lipsesc document_id sau source_key")
            yield metadata, cale_text
        except (OSError, ValueError, json.JSONDecodeError) as eroare:
            print(f"  EROARE metadata: {folder.name} — {eroare}")


def creeaza_chunkuri(continut):
    """Aplica chunking-ul regex, deduplicarea si split-ul secundar."""
    limita = int(len(continut) * PROCENT_MAXIM_CAUTARE_CUPRINS)
    potriviri_cuprins = list(PATTERN_LINIE_CUPRINS.finditer(continut[:limita]))
    if potriviri_cuprins:
        continut = continut[potriviri_cuprins[-1].end():]

    bucati = PATTERN_ARTICOL.split("\n" + continut)
    chunkuri_dupa_articol = {}

    for index in range(1, len(bucati), 2):
        articol = bucati[index].strip()
        text = bucati[index + 1].strip() if index + 1 < len(bucati) else ""
        if len(text) < LUNGIME_MINIMA_CHUNK:
            continue
        if articol not in chunkuri_dupa_articol or len(text) > len(chunkuri_dupa_articol[articol]["text"]):
            chunkuri_dupa_articol[articol] = {"articol": articol, "text": text}

    chunkuri_finale = []
    for chunk in chunkuri_dupa_articol.values():
        if len(chunk["text"]) < LUNGIME_PENTRU_SPLIT_SECUNDAR:
            chunkuri_finale.append(chunk)
            continue

        bucati_secundare = PATTERN_SUBPUNCT.split(chunk["text"])
        if len(bucati_secundare) == 1:
            chunkuri_finale.append(chunk)
            continue

        text_intro = bucati_secundare[0].strip()
        if len(text_intro) >= LUNGIME_MINIMA_CHUNK:
            chunkuri_finale.append({"articol": chunk["articol"], "text": text_intro})

        for index in range(1, len(bucati_secundare), 2):
            subpunct = bucati_secundare[index]
            text_subpunct = bucati_secundare[index + 1].strip() if index + 1 < len(bucati_secundare) else ""
            if len(text_subpunct) >= LUNGIME_MINIMA_CHUNK:
                chunkuri_finale.append({"articol": f"{chunk['articol']}({subpunct})", "text": text_subpunct})

    return chunkuri_finale


def conecteaza_baza_de_date():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT"),
    )


def importa_document(cursor, client_voyage, metadata, chunkuri):
    """Reinlocuieste atomic doar chunk-urile sursei curente."""
    sursa = metadata["source_key"]
    cursor.execute("DELETE FROM documente_chunks WHERE sursa = %s", (sursa,))

    for chunk in chunkuri:
        embedding = client_voyage.embed([chunk["text"]], model="voyage-3.5", input_type="document").embeddings[0]
        cursor.execute(
            "INSERT INTO documente_chunks (articol, text, embedding, sursa) VALUES (%s, %s, %s, %s)",
            (chunk["articol"], chunk["text"], embedding, sursa),
        )


def main():
    parser = argparse.ArgumentParser(description="Importa documente Omnia in Supabase")
    parser.add_argument("--dry-run", action="store_true", help="valideaza chunking-ul fara DB sau apeluri Voyage")
    args = parser.parse_args()

    documente = []
    for metadata, cale_text in gaseste_documente():
        continut = cale_text.read_text(encoding="utf-8")
        chunkuri = creeaza_chunkuri(continut)
        documente.append((metadata, chunkuri))
        print(f"  {metadata['document_id']}: {len(chunkuri)} chunk-uri")

    if not documente:
        print("Nu exista documente valide de importat.")
        return

    total = sum(len(chunkuri) for _, chunkuri in documente)
    if args.dry_run:
        print(f"\nDRY RUN: {total} chunk-uri validate din {len(documente)} documente. Nu s-a apelat Voyage si nu s-a modificat Supabase.")
        return

    load_dotenv(ROOT_PROIECT / ".env")
    client_voyage = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))
    conexiune = conecteaza_baza_de_date()

    try:
        with conexiune.cursor() as cursor:
            for metadata, chunkuri in documente:
                importa_document(cursor, client_voyage, metadata, chunkuri)
        conexiune.commit()
        print(f"\nImport finalizat: {total} chunk-uri din {len(documente)} documente.")
    except Exception:
        conexiune.rollback()
        raise
    finally:
        conexiune.close()


if __name__ == "__main__":
    main()
