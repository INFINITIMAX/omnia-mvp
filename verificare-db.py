import os
import psycopg2
from dotenv import load_dotenv

# Incarca variabilele din fisierul .env (acolo ai user/parola/host pentru baza de date)
load_dotenv()

# Deschide o conexiune catre baza de date PostgreSQL
conexiune = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT")
)

# Cursorul e "unealta" prin care trimiti comenzi SQL si citesti rezultate
cursor = conexiune.cursor()

# Interogare: numara cate chunk-uri exista, grupate pe fiecare document sursa
cursor.execute("""
    SELECT sursa, COUNT(*) AS numar_chunkuri
    FROM documente_chunks
    GROUP BY sursa
    ORDER BY numar_chunkuri DESC;
""")

# fetchall() aduce toate randurile rezultate, ca o lista de tupluri
rezultate = cursor.fetchall()

# Calculam si totalul general, ca sa il afisam la final
total_chunkuri = sum(numar for _, numar in rezultate)

print("=" * 50)
print("STARE BAZA DE DATE OMNIA")
print("=" * 50)

for sursa, numar in rezultate:
    print(f"{sursa:<35} {numar:>5} chunk-uri")

print("-" * 50)
print(f"{'TOTAL':<35} {total_chunkuri:>5} chunk-uri")
print(f"{'Documente distincte':<35} {len(rezultate):>5}")
print("=" * 50)

# Inchidem cursorul si conexiunea, e o buna practica sa nu le lasi deschise
cursor.close()
conexiune.close()