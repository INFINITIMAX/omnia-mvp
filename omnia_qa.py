from dotenv import load_dotenv
import os
import voyageai
import psycopg2
from anthropic import Anthropic

load_dotenv()

vo = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD")
)
cursor = conn.cursor()


def cauta_articol_exact(articol, sursa=None):
    if sursa:
        cursor.execute(
            "SELECT sursa, articol, text FROM documente_chunks WHERE articol = %s AND sursa = %s",
            (articol, sursa)
        )
    else:
        cursor.execute(
            "SELECT sursa, articol, text FROM documente_chunks WHERE articol = %s",
            (articol,)
        )
    return cursor.fetchall()


def cauta_chunks_relevante(intrebare, numar_rezultate=3):
    embedding_intrebare = vo.embed([intrebare], model="voyage-3.5", input_type="query").embeddings[0]

    cursor.execute(
        """
        SELECT sursa, articol, text
        FROM documente_chunks
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """,
        (embedding_intrebare, numar_rezultate)
    )
    return cursor.fetchall()


def construieste_context(chunks_relevante):
    context = ""
    for sursa, articol, text in chunks_relevante:
        context += f"\n[Sursa: {sursa}, Articol {articol}]\n{text}\n"
    return context

    
def cauta_exhaustiv(intrebare, prag_similaritate=0.5):
    embedding_intrebare = vo.embed([intrebare], model="voyage-3.5", input_type="query").embeddings[0]

    cursor.execute(
        """
        SELECT sursa, articol, text, 1 - (embedding <=> %s::vector) AS similaritate
        FROM documente_chunks
        WHERE 1 - (embedding <=> %s::vector) > %s
        ORDER BY similaritate DESC
        """,
        (embedding_intrebare, embedding_intrebare, prag_similaritate)
    )
    return cursor.fetchall()


def interpreteaza_cu_toate_sursele(intrebare):
    rezultate = cauta_exhaustiv(intrebare)
    
    if not rezultate:
        return "Nu am gasit nicio informatie relevanta in documente."
    
    context = ""
    for sursa, articol, text, similaritate in rezultate:
        context += f"\n[Sursa: {sursa}, Articol {articol}]\n{text}\n"

    raspuns = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        system=f"""Esti un asistent care raspunde STRICT pe baza fragmentelor de mai jos.

REGULI OBLIGATORII:
1. Mai intai, LISTEAZA fiecare articol relevant gasit, cu sursa si citatul exact.
2. Apoi, ofera o interpretare/sinteza scurta, bazata STRICT pe aceste citate.
3. Daca fragmentele se contrazic, mentioneaza explicit conflictul.
4. Nu inventa, nu adauga cunostinte generale care nu apar in fragmente.

FRAGMENTE GASITE:
{context}""",
        messages=[{"role": "user", "content": intrebare}]
    )
    return raspuns.content[0].text

def intreaba_omnia(intrebare):
    # Pasul 1: cauta chunk-urile relevante (nu tot documentul!)
    chunks_relevante = cauta_chunks_relevante(intrebare)
    context = construieste_context(chunks_relevante)

    # Pasul 2: trimite doar contextul relevant catre Claude
    raspuns = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        system=f"""Esti un asistent care raspunde STRICT pe baza fragmentelor de document de mai jos.

REGULI OBLIGATORII:
1. Raspunde DOAR pe baza informatiei gasite in fragmentele furnizate.
2. Citeaza EXACT sursa (numele documentului) SI articolul din care provine raspunsul.
3. Daca informatia NU se gaseste in fragmentele furnizate, raspunde EXACT: "Nu am gasit aceasta informatie in document."
4. Nu inventa, nu presupune, nu completa cu cunostinte generale.

FRAGMENTE RELEVANTE:
{context}""",
        messages=[
            {"role": "user", "content": intrebare}
        ]
    )
    return raspuns.content[0].text

print("=== Omnia - Asistent normative ===")
print("Scrie 'exit' pentru a iesi.\n")

while True:
    intrebare = input("Intrebarea ta: ")
    if intrebare.lower() == "exit":
        break
    print()
    print(interpreteaza_cu_toate_sursele(intrebare))
    print()
cursor.close()
conn.close()