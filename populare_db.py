from dotenv import load_dotenv
import os
import re
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

# Lista de documente de procesat
documente = ["normativ_1.txt", "normativ_2.txt", "normativ_3.txt", "NP0572002_extras.txt"]

# Regex final: prinde 3 tipuri de headere -> articole cu litera intre paranteze,
# ANEXA, si articole cu cifre multiple fara paranteza (ex. cap. 3.3)
pattern_articol = re.compile(
    r'\n\s*(\d+\.\d+\.\s*\([A-Za-z]\)\.\s*(?:[IVXLl]\.|\d+\.)?(?:\d+\.)?|ANEXA\s+\d+\.\d+\.|\d+\.\d+\.(?:\d+\.){0,4})'
)

# Detectare linii de cuprins (titlu....123), ca sa le eliminam inainte de chunking
pattern_linie_cuprins = re.compile(r'\.{2,}\s*\d{1,4}\s*(?=\n|$)')

LUNGIME_MINIMA_CHUNK = 15  # sub atatea caractere, consideram chunk-ul junk

# Golim tabelul, ca sa nu duplicam
cursor.execute("DELETE FROM documente_chunks;")

total_chunks = 0
total_junk = 0

for nume_fisier in documente:
    with open(nume_fisier, "r", encoding="utf-8") as fisier:
        continut = fisier.read()

    # Eliminam cuprinsul, daca exista (cautam ultima linie de tip "titlu....123")
    potriviri_cuprins = list(pattern_linie_cuprins.finditer(continut))
    if potriviri_cuprins:
        pozitie_sfarsit = potriviri_cuprins[-1].end()
        continut = continut[pozitie_sfarsit:]

    # \n artificial la inceput, ca regex-ul sa prinda si primul articol
    continut = "\n" + continut

    bucati = pattern_articol.split(continut)

    chunks_document = 0
    for i in range(1, len(bucati), 2):
        numar_articol = bucati[i].strip()
        text = bucati[i + 1].strip() if i + 1 < len(bucati) else ""

        if not text:
            continue
        if len(text) < LUNGIME_MINIMA_CHUNK:
            total_junk += 1
            continue

        embedding = vo.embed([text], model="voyage-3.5", input_type="document").embeddings[0]

        cursor.execute(
            "INSERT INTO documente_chunks (articol, text, embedding, sursa) VALUES (%s, %s, %s, %s)",
            (numar_articol, text, embedding, nume_fisier)
        )
        total_chunks += 1
        chunks_document += 1

    print(f"  {nume_fisier}: {chunks_document} chunk-uri")

conn.commit()
print(f"\nAm salvat {total_chunks} chunk-uri din {len(documente)} documente. ({total_junk} eliminate ca junk)")

cursor.close()
conn.close()


#functional but placeholder, this part will become an agent at a moment in time