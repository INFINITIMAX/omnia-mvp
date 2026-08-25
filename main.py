from dotenv import load_dotenv
import os
import voyageai
import psycopg2
from anthropic import Anthropic
from fastapi import FastAPI, Depends
from pydantic import BaseModel

load_dotenv()

# Clientii pentru Voyage (embeddings) si Claude (generare raspuns) sunt "fara
# stare" (stateless) -- nu tin o conexiune vie ca la baza de date, doar fac
# apeluri HTTP la nevoie. De asta e sigur sa fie create o singura data, la
# pornirea serverului, si refolosite pentru toate cererile.
vo = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

app = FastAPI()


# "Dependency" FastAPI: o functie care ruleaza AUTOMAT inainte de fiecare
# cerere care o cere (prin Depends(...) mai jos). "yield" (in loc de
# "return") ii spune lui FastAPI: da conexiunea catre endpoint, lasa-l
# sa o foloseasca, iar cand endpoint-ul termina (cu succes SAU cu eroare),
# revino aici si ruleaza tot ce e DUPA yield -- garantand ca inchidem
# mereu conexiunea, per cerere, fara sa o partajam intre useri diferiti.
def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT")
    )
    try:
        yield conn
    finally:
        conn.close()


# Pydantic BaseModel: descrie forma pe care TREBUIE sa o aiba corpul JSON
# trimis de client (ex: {"intrebare": "..."}). FastAPI valideaza automat --
# daca cererea nu are campul "intrebare" de tip text, respinge cu eroare
# clara, inainte sa ajunga in codul nostru.
class IntrebareRequest(BaseModel):
    intrebare: str


def cauta_exhaustiv(conn, intrebare, prag_similaritate=0.5):
    embedding_intrebare = vo.embed([intrebare], model="voyage-3.5", input_type="query").embeddings[0]

    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT sursa, articol, text, 1 - (embedding <=> %s::vector) AS similaritate
        FROM documente_chunks
        WHERE 1 - (embedding <=> %s::vector) > %s
        ORDER BY similaritate DESC
        """,
        (embedding_intrebare, embedding_intrebare, prag_similaritate)
    )
    rezultate = cursor.fetchall()
    cursor.close()
    return rezultate


def interpreteaza_cu_toate_sursele(conn, intrebare):
    rezultate = cauta_exhaustiv(conn, intrebare)

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


# "@app.post" inregistreaza aceasta functie ca handler pentru
# POST /intreaba. "conn: psycopg2.extensions.connection = Depends(get_db_connection)"
# ii spune lui FastAPI: inainte sa rulezi aceasta functie, ruleaza
# get_db_connection() si baga rezultatul in parametrul "conn".
@app.post("/intreaba")
def intreaba(cerere: IntrebareRequest, conn=Depends(get_db_connection)):
    raspuns = interpreteaza_cu_toate_sursele(conn, cerere.intrebare)
    return {"raspuns": raspuns}
