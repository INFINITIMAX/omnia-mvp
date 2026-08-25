from dotenv import load_dotenv
import os
import re
import glob
import voyageai
import psycopg2

load_dotenv()

vo = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT")
)
cursor = conn.cursor()

# Nu mai scriem manual o lista de fisiere -- scanam automat folderul
# documente_noi si luam toate fisierele .txt gasite acolo (extrase deja
# din PDF de catre procesare_documente.py).
FOLDER_DOCUMENTE = "documente_noi"
tipar_cautare = os.path.join(FOLDER_DOCUMENTE, "*.txt")
documente = glob.glob(tipar_cautare)

print(f"Am gasit {len(documente)} fisiere .txt in folderul '{FOLDER_DOCUMENTE}'.")

# Regex final: prinde 3 tipuri de headere -> articole cu litera intre paranteze,
# ANEXA, si articole cu cifre multiple fara paranteza (ex. cap. 3.3)
pattern_articol = re.compile(
    r'\n\s*(\d+\.\d+\.\s*\([A-Za-z]\)\.\s*(?:[IVXLl]\.|\d+\.)?(?:\d+\.)?|ANEXA\s+\d+\.\d+\.|\d+\.\d+\.(?:\d+\.){0,4})'
)

# Detectare linii de cuprins (titlu....123), ca sa le eliminam inainte de chunking.
# Limitam cautarea la primele 20% din document -- cuprinsul e mereu la inceput,
# iar daca am cauta in tot documentul am risca sa taiem gresit alt tabel/lista
# numerotata gasita din intamplare mult mai tarziu.
pattern_linie_cuprins = re.compile(r'\.{2,}\s*\d{1,4}\s*(?=\n|$)')
PROCENT_MAXIM_CAUTARE_CUPRINS = 0.20

LUNGIME_MINIMA_CHUNK = 15  # sub atatea caractere, consideram chunk-ul junk
LUNGIME_PENTRU_SPLIT_SECUNDAR = 2000  # peste atatea caractere, incercam split suplimentar

# Regex pentru paragrafe numerotate "(1)", "(2)" etc., folosit la split-ul secundar
pattern_subpunct = re.compile(r'\n\s*\((\d+)\)\s+')

# Golim tabelul, ca sa nu duplicam
cursor.execute("DELETE FROM documente_chunks;")

total_chunks = 0
total_junk = 0

for cale_fisier in documente:
    nume_fisier = os.path.basename(cale_fisier)

    with open(cale_fisier, "r", encoding="utf-8") as fisier:
        continut = fisier.read()

    # Eliminam cuprinsul, daca exista, cautand doar in primele 20% din document
    limita_cautare = int(len(continut) * PROCENT_MAXIM_CAUTARE_CUPRINS)
    potriviri_cuprins = list(pattern_linie_cuprins.finditer(continut[:limita_cautare]))
    if potriviri_cuprins:
        pozitie_sfarsit = potriviri_cuprins[-1].end()
        continut = continut[pozitie_sfarsit:]

    # \n artificial la inceput, ca regex-ul sa prinda si primul articol
    continut = "\n" + continut

    bucati = pattern_articol.split(continut)

    chunks_document = {}  # articol -> {"articol": ..., "text": ...}, pentru deduplicare
    junk_document = 0

    for i in range(1, len(bucati), 2):
        numar_articol = bucati[i].strip()
        text = bucati[i + 1].strip() if i + 1 < len(bucati) else ""

        if not text:
            continue
        if len(text) < LUNGIME_MINIMA_CHUNK:
            junk_document += 1
            continue

        # Deduplicare: daca acelasi numar de articol apare de mai multe ori
        # (ex. o data in cuprins nedetectat, o data cu textul real), pastram
        # varianta cu cel mai mult text.
        if numar_articol not in chunks_document or len(text) > len(chunks_document[numar_articol]["text"]):
            chunks_document[numar_articol] = {"articol": numar_articol, "text": text}

    # Split secundar: chunk-urile prea mari (>2000 caractere) sunt taiate
    # suplimentar dupa markeri "(1)", "(2)" etc., daca exista.
    chunks_finale = []
    for c in chunks_document.values():
        if len(c["text"]) < LUNGIME_PENTRU_SPLIT_SECUNDAR:
            chunks_finale.append(c)
            continue

        bucati_secundare = pattern_subpunct.split(c["text"])
        if len(bucati_secundare) == 1:
            chunks_finale.append(c)
            continue

        text_intro = bucati_secundare[0].strip()
        if len(text_intro) >= LUNGIME_MINIMA_CHUNK:
            chunks_finale.append({"articol": c["articol"], "text": text_intro})

        for i in range(1, len(bucati_secundare), 2):
            numar_subpunct = bucati_secundare[i]
            text_subpunct = bucati_secundare[i + 1].strip() if i + 1 < len(bucati_secundare) else ""
            if text_subpunct and len(text_subpunct) >= LUNGIME_MINIMA_CHUNK:
                articol_nou = f"{c['articol']}({numar_subpunct})"
                chunks_finale.append({"articol": articol_nou, "text": text_subpunct})

    for c in chunks_finale:
        embedding = vo.embed([c["text"]], model="voyage-3.5", input_type="document").embeddings[0]

        cursor.execute(
            "INSERT INTO documente_chunks (articol, text, embedding, sursa) VALUES (%s, %s, %s, %s)",
            (c["articol"], c["text"], embedding, nume_fisier)
        )
        total_chunks += 1

    total_junk += junk_document
    print(f"  {nume_fisier}: {len(chunks_finale)} chunk-uri")

conn.commit()
print(f"\nAm salvat {total_chunks} chunk-uri din {len(documente)} documente. ({total_junk} eliminate ca junk)")

cursor.close()
conn.close()


#functional but placeholder, this part will become an agent at a moment in time
