from dotenv import load_dotenv
import os
import voyageai
import psycopg2

load_dotenv()

vo = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD")
)
cursor = conn.cursor()

intrebare = "Câte ascensoare sunt necesare la o clădire cu mai mult de P+5 etaje?"

embedding_intrebare = vo.embed([intrebare], model="voyage-3.5", input_type="query").embeddings[0]

# Calculam similaritatea exacta fata de chunk-ul specific 3.2.(B).l.
cursor.execute(
    """
    SELECT articol, 1 - (embedding <=> %s::vector) AS similaritate
    FROM documente_chunks
    WHERE articol = %s AND sursa = %s
    """,
    (embedding_intrebare, "3.2.(B).l.", "NP0572002_extras.txt")
)
rezultat = cursor.fetchone()
print(f"Similaritate fata de chunk-ul corect [3.2.(B).l.]: {rezultat[1]:.4f}" if rezultat else "Chunk-ul nu a fost gasit cu acest nume exact.")

# Bonus: vedem top 5 cele mai similare chunk-uri, indiferent de prag, ca sa vedem unde se plaseaza cel corect
print("\n=== Top 5 cele mai similare chunk-uri (fara prag) ===")
cursor.execute(
    """
    SELECT sursa, articol, 1 - (embedding <=> %s::vector) AS similaritate
    FROM documente_chunks
    ORDER BY similaritate DESC
    LIMIT 5
    """,
    (embedding_intrebare,)
)
for sursa, articol, sim in cursor.fetchall():
    print(f"  {sim:.4f} -> [{articol}] ({sursa})")

cursor.close()
conn.close()