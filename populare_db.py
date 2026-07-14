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
    password=os.getenv("DB_PASSWORD")
)
cursor = conn.cursor()

# Lista de documente de procesat
documente = ["normativ_1.txt", "normativ_2.txt"]

pattern = r'(\d+\.\d+(?:\.\d+)?(?:\.\d+)?\.)'

# Golim tabelul, ca sa nu duplicam
cursor.execute("DELETE FROM documente_chunks;")

total_chunks = 0

for nume_fisier in documente:
    with open(nume_fisier, "r", encoding="utf-8") as fisier:
        continut = fisier.read()

    bucati = re.split(pattern, continut)

    for i in range(1, len(bucati), 2):
        numar_articol = bucati[i].strip()
        text = bucati[i + 1].strip() if i + 1 < len(bucati) else ""
        
        if text:
            embedding = vo.embed([text], model="voyage-3.5", input_type="document").embeddings[0]
            
            cursor.execute(
                "INSERT INTO documente_chunks (articol, text, embedding, sursa) VALUES (%s, %s, %s, %s)",
                (numar_articol, text, embedding, nume_fisier)
            )
            total_chunks += 1

conn.commit()
print(f"Am salvat {total_chunks} chunk-uri din {len(documente)} documente.")

cursor.close()
conn.close()