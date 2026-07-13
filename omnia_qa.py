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


def cauta_chunks_relevante(intrebare, numar_rezultate=3):
    embedding_intrebare = vo.embed([intrebare], model="voyage-3.5", input_type="query").embeddings[0]

    cursor.execute(
        """
        SELECT articol, text
        FROM documente_chunks
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """,
        (embedding_intrebare, numar_rezultate)
    )
    return cursor.fetchall()


def construieste_context(chunks_relevante):
    context = ""
    for articol, text in chunks_relevante:
        context += f"\n[Articol {articol}]\n{text}\n"
    return context


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
2. Citeaza EXACT articolul din care provine raspunsul.
3. Daca informatia NU se gaseste in fragmentele furnizate, raspunde EXACT: "Nu am gasit aceasta informatie in document."
4. Nu inventa, nu presupune, nu completa cu cunostinte generale.

FRAGMENTE RELEVANTE:
{context}""",
        messages=[
            {"role": "user", "content": intrebare}
        ]
    )
    return raspuns.content[0].text


# Teste
intrebari = [
    "Cum sunt clasificate starile limita?",
    "Ce trebuie sa contina modelul de calcul?",
    "Care este distanta minima pentru o pompa de caldura?"
]

for intrebare in intrebari:
    print(f"--- {intrebare} ---")
    print(intreaba_omnia(intrebare))
    print()

cursor.close()
conn.close()