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
    password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT")
)
cursor = conn.cursor()

intrebare = "Cum sunt clasificate starile limita?"
embedding_intrebare = vo.embed([intrebare], model="voyage-3.5", input_type="query").embeddings[0]

cursor.execute(
    """
    SELECT articol, text, 1 - (embedding <=> %s::vector) AS similaritate
    FROM documente_chunks
    ORDER BY embedding <=> %s::vector
    LIMIT 3
    """,
    (embedding_intrebare, embedding_intrebare)
)

rezultate = cursor.fetchall()

print(f"Intrebare: {intrebare}\n")
for articol, text, similaritate in rezultate:
    print(f"Articol {articol} (similaritate: {similaritate:.4f})")
    print(f"{text[:100]}...\n")

cursor.close()
conn.close()