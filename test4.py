from dotenv import load_dotenv
import os
import psycopg2

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD")
)
cursor = conn.cursor()

# 1. Total chunk-uri per document, ca sa confirmam ce e efectiv in DB acum
cursor.execute("SELECT sursa, COUNT(*) FROM documente_chunks GROUP BY sursa ORDER BY sursa;")
print("=== Total chunk-uri per document ===")
for sursa, numar in cursor.fetchall():
    print(f"  {sursa}: {numar} chunk-uri")

# 2. Cautam direct in TEXT (nu in numele articolului) cuvantul "ascensor"
cursor.execute(
    "SELECT sursa, articol, LEFT(text, 150) FROM documente_chunks WHERE text ILIKE %s AND sursa = %s",
    ("%ascensor%", "NP0572002_extras.txt")
)
rezultate = cursor.fetchall()

print(f"\n=== Chunk-uri care contin cuvantul 'ascensor' in text ===")
print(f"Gasite: {len(rezultate)}\n")
for sursa, articol, text_inceput in rezultate:
    print(f"[{articol}]")
    print(f"  {text_inceput}")
    print("---")

# 3. Verificam si toate articolele din capitolul 3.2, ca sa vedem structura reala
cursor.execute(
    "SELECT articol FROM documente_chunks WHERE sursa = %s AND articol LIKE %s ORDER BY articol",
    ("NP0572002_extras.txt", "3.2%")
)
articole_32 = cursor.fetchall()
print(f"\n=== Toate articolele din capitolul 3.2 (NP0572002_extras.txt) ===")
print(f"Total: {len(articole_32)}")
for (art,) in articole_32:
    print(f"  {art}")

cursor.close()
conn.close()