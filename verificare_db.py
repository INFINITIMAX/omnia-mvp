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
 
# Total chunks in tabel
cursor.execute("SELECT COUNT(*) FROM documente_chunks;")
total = cursor.fetchone()[0]
print(f"Total chunk-uri in tabel: {total}")
 
# Din ce documente provin (sursa) si cate chunk-uri are fiecare
cursor.execute("SELECT sursa, COUNT(*) FROM documente_chunks GROUP BY sursa ORDER BY sursa;")
rezultate = cursor.fetchall()
 
print("\nDefalcare pe documente:")
for sursa, numar in rezultate:
    print(f"  {sursa}: {numar} chunk-uri")
 
cursor.close()
conn.close()
 