import re

with open("normativ_1.txt", "r", encoding="utf-8") as fisier:
    continut = fisier.read()

# Pattern: gaseste toate locurile unde incepe un articol (ex: "3.1.3.2.")
pattern = r'(\d+\.\d+\.\d+(?:\.\d+)?\.)'

# Impartim textul dupa acest pattern
bucati = re.split(pattern, continut)

chunks = []
id_chunk = 1

# Bucatile vin in perechi: numar_articol + text_dupa
for i in range(1, len(bucati), 2):
    numar_articol = bucati[i].strip()
    text = bucati[i + 1].strip() if i + 1 < len(bucati) else ""
    
    chunks.append({
        "id": id_chunk,
        "articol": numar_articol,
        "text": text
    })
    id_chunk += 1

# Verificam rezultatul
for chunk in chunks:
    print(f"--- Articol {chunk['articol']} ---")
    print(chunk['text'][:100])
    print()