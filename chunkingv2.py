import re
 
# ============================================================
# Regex principal: prinde headere de tip 3.4.(E).2.1. sau 3.4.(E). 1.4.
# extins sa prinda si varianta cu cifra romana: 3.4.(F).I. sau 3.4.(G).l.
# ============================================================
pattern_articol = re.compile(
    r'\n\s*(\d+\.\d+\.\s*\([A-Za-z]\)\.\s*(?:[IVXLl]\.|\d+\.)?(?:\d+\.)?|ANEXA\s+\d+\.\d+\.|\d+\.\d+\.(?:\d+\.){1,4})'
)
 
nume_fisier = "NP0572002_extras.txt"
 
with open(nume_fisier, "r", encoding="utf-8") as fisier:
    continut = fisier.read()
 
# ============================================================
# Pasul 1: detectam si taiem cuprinsul
# Cautam linii de tip "titlu..........123" (puncte de aliniere + numar de pagina)
# ============================================================
pattern_linie_cuprins = re.compile(r'\.{2,}\s*\d{1,4}\s*(?=\n|$)')
 
potriviri_cuprins = list(pattern_linie_cuprins.finditer(continut))
print(f"Linii de tip cuprins detectate: {len(potriviri_cuprins)}")
 
if potriviri_cuprins:
    ultima_potrivire = potriviri_cuprins[-1]
    pozitie_sfarsit_cuprins = ultima_potrivire.end()
    print(f"Cuprinsul pare sa se termine la caracterul {pozitie_sfarsit_cuprins} din {len(continut)}")
    continut_fara_cuprins = continut[pozitie_sfarsit_cuprins:]
else:
    print("Nu am gasit pattern de cuprins, folosesc tot documentul.")
    continut_fara_cuprins = continut
 
print(f"Text ramas dupa eliminare cuprins: {len(continut_fara_cuprins)} caractere (din {len(continut)} initial)")
print()
 
# Adaugam un \n artificial la inceput, ca sa se prinda si primul header
# (regex-ul cere \n inainte de fiecare header, dar primul poate sa nu aiba unul dupa taierea cuprinsului)
continut_fara_cuprins = "\n" + continut_fara_cuprins
 
# --- Chunking efectiv folosind pattern_articol, pe textul FARA cuprins ---
bucati = pattern_articol.split(continut_fara_cuprins)
 
# bucati[0] = text inainte de primul articol gasit (de obicei titlu/intro, il ignoram sau il pastram separat)
# apoi alterneaza: [header, text, header, text, ...]
 
LUNGIME_MINIMA_CHUNK = 15  # sub atatea caractere, consideram chunk-ul zgomot/junk
 
chunks = []
chunks_junk = []
for i in range(1, len(bucati), 2):
    header = bucati[i].strip()
    text = bucati[i + 1].strip() if i + 1 < len(bucati) else ""
    if not text:
        continue
    if len(text) < LUNGIME_MINIMA_CHUNK:
        chunks_junk.append({"articol": header, "text": text})
    else:
        chunks.append({"articol": header, "text": text})
 
print(f"Total chunk-uri valide: {len(chunks)}")
print(f"Chunk-uri eliminate ca junk (sub {LUNGIME_MINIMA_CHUNK} caractere): {len(chunks_junk)}")
if chunks_junk:
    print("Exemple de junk eliminat:")
    for c in chunks_junk[:10]:
        print(f"  [{c['articol']}] -> '{c['text']}'")
print()
 
# --- Afisam primele 5 chunk-uri ca sa verificam manual ---
print("=== Primele 5 chunk-uri ===\n")
for c in chunks[:5]:
    print(f"[{c['articol']}]")
    print(c['text'][:200].replace("\n", " "))
    print("---")
 
# --- Afisam si 5 chunk-uri din mijlocul documentului, pt verificare suplimentara ---
mijloc = len(chunks) // 2
print("\n=== 5 chunk-uri din mijlocul documentului ===\n")
for c in chunks[mijloc:mijloc + 5]:
    print(f"[{c['articol']}]")
    print(c['text'][:200].replace("\n", " "))
    print("---")
 
# --- Statistici lungime chunk-uri, ca sa vedem daca sunt prea mari/mici ---
lungimi = [len(c['text']) for c in chunks]
if lungimi:
    print(f"\nLungime medie chunk: {sum(lungimi) // len(lungimi)} caractere")
    print(f"Cel mai scurt chunk: {min(lungimi)} caractere")
    print(f"Cel mai lung chunk: {max(lungimi)} caractere")
 
# --- Diagnostic: gasim si afisam chunk-ul cel mai lung (inceput + sfarsit) ---
chunk_lung = max(chunks, key=lambda c: len(c['text']))
print(f"\n=== Chunk-ul cel mai lung: [{chunk_lung['articol']}] ({len(chunk_lung['text'])} caractere) ===")
print("--- Inceput ---")
print(chunk_lung['text'][:300])
print("--- Sfarsit ---")
print(chunk_lung['text'][-300:])
 
# --- Diagnostic: cautam in chunk-ul cel mai lung orice pattern posibil de header ratat ---
print(f"\n=== Cautare headere posibil ratate in chunk-ul cel mai lung ===")
pattern_posibil_header = re.compile(r'\n\s*(\d+\.\d+[^\n]{0,30})')
candidati = pattern_posibil_header.findall(chunk_lung['text'])
print(f"Candidati gasiti: {len(candidati)}")
for cand in candidati[:20]:
    print(f"  -> '{cand.strip()}'")
 
# --- Diagnostic: afisam cele mai scurte 5 chunk-uri, integral ---
chunks_sortate = sorted(chunks, key=lambda c: len(c['text']))
print(f"\n=== Cele mai scurte 5 chunk-uri (integral) ===")
for c in chunks_sortate[:5]:
    print(f"[{c['articol']}] -> '{c['text']}'")
 
# --- Diagnostic: unde pare sa se termine cuprinsul? cautam primul chunk care NU contine "....." sau numere de pagina izolate ---
print(f"\n=== Verificare cuprins: primele 10 chunk-uri, cu lungime ===")
for i, c in enumerate(chunks[:10]):
    are_puncte_pagina = "...." in c['text'] or bool(re.search(r'\.\s*\d{1,3}\s*$', c['text'][:50]))
    print(f"{i}: [{c['articol']}] len={len(c['text'])} suspect_cuprins={are_puncte_pagina}")