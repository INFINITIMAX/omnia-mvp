from dotenv import load_dotenv
import os
import re
import voyageai
import psycopg2

load_dotenv()

# Conectare Voyage
vo = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))

# Conectare baza de date
conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD")
)
cursor = conn.cursor()

# Citire si chunking document
with open("normativ_1.txt", "r", encoding="utf-8") as fisier:
    continut = fisier.read()

pattern = r'(\d+\.\d+\.\d+(?:\.\d+)?\.)'
bucati = re.split(pattern, continut)

chunks = []
for i in range(1, len(bucati), 2):
    numar_articol = bucati[i].strip()
    text = bucati[i + 1].strip() if i + 1 < len(bucati) else ""
    if text:
        chunks.append({"articol": numar_articol, "text": text})

# Golim tabelul (ca sa nu duplicam la fiecare rulare)
cursor.execute("DELETE FROM documente_chunks;")

# Pentru fiecare chunk: generam embedding si salvam in baza de date
for chunk in chunks:
    embedding = vo.embed([chunk["text"]], model="voyage-3.5", input_type="document").embeddings[0]
    
    cursor.execute(
        "INSERT INTO documente_chunks (articol, text, embedding) VALUES (%s, %s, %s)",
        (chunk["articol"], chunk["text"], embedding)
    )

conn.commit()
print(f"Am salvat {len(chunks)} chunk-uri in baza de date.")

cursor.close()
conn.close()