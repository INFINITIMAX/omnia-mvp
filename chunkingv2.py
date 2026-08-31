import re

# ============================================================
# Regex principal: prinde headere de tip 3.4.(E).2.1. sau 3.4.(E). 1.4.
# extins sa prinda si varianta cu cifra romana: 3.4.(F).I. sau 3.4.(G).l.
# ============================================================
pattern_articol = re.compile(
    r'\n\s*(\d+\.\d+\.\s*\([A-Za-z]\)\.\s*(?:[IVXLl]\.|\d+\.)?(?:\d+\.)?|ANEXA\s+\d+\.\d+\.|\d+\.\d+\.(?:\d+\.){0,4})'
)

nume_fisier = "documente_noi/np010_2022/extracted.txt"

with open(nume_fisier, "r", encoding="utf-8") as fisier:
    continut = fisier.read()

# ============================================================
# Pasul 1: detectam si taiem cuprinsul
# Cautam linii de tip "titlu..........123" (puncte de aliniere + numar de pagina)
# ============================================================
pattern_linie_cuprins = re.compile(r'\.{2,}\s*\d{1,4}\s*(?=\n|$)')

# LIMITAM cautarea liniilor de cuprins doar la primele 20% din document.
# De ce: cuprinsul unui document apare mereu la INCEPUT, niciodata la mijloc
# sau la sfarsit. Daca cautam in tot documentul, riscam sa gasim din intamplare
# alt tipar similar (ex. un tabel, o lista de referinte) mult mai tarziu,
# si sa taiem gresit aproape tot documentul inainte de acel punct.
PROCENT_MAXIM_CAUTARE_CUPRINS = 0.20
limita_cautare = int(len(continut) * PROCENT_MAXIM_CAUTARE_CUPRINS)
zona_de_cautat = continut[:limita_cautare]

potriviri_cuprins = list(pattern_linie_cuprins.finditer(zona_de_cautat))
print(f"Linii de tip cuprins detectate (in primele {PROCENT_MAXIM_CAUTARE_CUPRINS:.0%} din document): {len(potriviri_cuprins)}")

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

print(f"Total chunk-uri valide (inainte de deduplicare): {len(chunks)}")
print(f"Chunk-uri eliminate ca junk (sub {LUNGIME_MINIMA_CHUNK} caractere): {len(chunks_junk)}")
if chunks_junk:
    print("Exemple de junk eliminat:")
    for c in chunks_junk[:10]:
        print(f"  [{c['articol']}] -> '{c['text']}'")
print()

# ============================================================
# Pasul 2: deduplicare dupa numarul articolului.
#
# Problema: unele documente scriu cuprinsul FARA puncte de aliniere
# (ex. "Siguranta circulatiei  15"), pe care regex-ul de eliminare a
# cuprinsului nu il recunoaste. Rezultatul: acelasi numar de articol
# apare de 2 ori -- o data scurt, din cuprins, o data cu tot textul
# real, mai jos in document.
#
# Solutia: in loc sa incercam sa recunoastem FIECARE stil posibil de
# cuprins (nesfarsit de variatii), atacam simptomul direct -- daca
# gasim duplicate, pastram doar varianta cu CEL MAI MULT text (aproape
# sigur cea reala, nu rezumatul scurt din cuprins).
# ============================================================

# Un dictionar Python e o structura de tip "cheie -> valoare".
# Aici cheia e numele articolului (ex. "4.2.1."), iar valoarea e
# chunk-ul intreg (dictionarul cu articol+text) pentru acel articol.
chunks_unice = {}

for c in chunks:
    articol = c['articol']
    # Daca nu am mai vazut acest articol, sau daca varianta noua are
    # MAI MULT text decat cea deja salvata, o pastram pe cea noua.
    if articol not in chunks_unice or len(c['text']) > len(chunks_unice[articol]['text']):
        chunks_unice[articol] = c

numar_duplicate_eliminate = len(chunks) - len(chunks_unice)

# .values() ia doar valorile din dictionar (chunk-urile), fara cheile,
# si list(...) le transforma inapoi intr-o lista normala, ca inainte.
chunks = list(chunks_unice.values())

print(f"Duplicate eliminate (articol aparut de mai multe ori): {numar_duplicate_eliminate}")
print(f"Total chunk-uri valide (dupa deduplicare): {len(chunks)}")
print()

# ============================================================
# Pasul 3: taiere secundara, pentru chunk-urile prea mari.
#
# Am observat ca acest document foloseste des paragrafe numerotate
# de tipul "(1)  text...  (2)  text..." IN INTERIORUL unei sectiuni,
# fara alt numar de tip X.Y.Z. intre ele. Regex-ul principal nu vede
# aceste paranteze ca separatoare, deci sectiunea intreaga ramane
# un singur chunk urias.
#
# Solutia: pentru chunk-urile care depasesc un prag de lungime,
# incercam sa le taiem SUPLIMENTAR dupa markerii "(1)", "(2)", etc.
# ============================================================

LUNGIME_PENTRU_SPLIT_SECUNDAR = 2000  # doar chunk-urile mai mari de atat sunt candidate

# Acest regex prinde un numar intre paranteze, la inceput de rand,
# urmat de spatiu -- ex. "\n(1)  " sau "\n (2) ".
# Grupul de captura ((\d+)) retine DOAR cifra din interiorul parantezei.
pattern_subpunct = re.compile(r'\n\s*\((\d+)\)\s+')

chunks_finale = []
numar_chunkuri_splitate = 0

for c in chunks:
    # Daca acest chunk nu e suficient de mare, il pastram neschimbat
    if len(c['text']) < LUNGIME_PENTRU_SPLIT_SECUNDAR:
        chunks_finale.append(c)
        continue

    # .split() cu un regex care are un grup de captura intoarce o lista
    # alternata: [text_inainte_de_primul_(1), "1", text_dupa, "2", text_dupa, ...]
    bucati_secundare = pattern_subpunct.split(c['text'])

    # Daca lista are doar 1 element, inseamna ca regex-ul NU a gasit
    # niciun "(numar)" in acest chunk -- il lasam neschimbat.
    if len(bucati_secundare) == 1:
        chunks_finale.append(c)
        continue

    numar_chunkuri_splitate += 1

    # Prima bucata (index 0) e textul de INAINTE de primul "(1)" --
    # de obicei titlul sectiunii. O pastram ca un chunk separat, doar
    # daca are continut relevant (nu doar cateva caractere goale).
    text_intro = bucati_secundare[0].strip()
    if len(text_intro) >= LUNGIME_MINIMA_CHUNK:
        chunks_finale.append({"articol": c['articol'], "text": text_intro})

    # Restul listei alterneaza: numar, text, numar, text...
    for i in range(1, len(bucati_secundare), 2):
        numar_subpunct = bucati_secundare[i]
        text_subpunct = bucati_secundare[i + 1].strip() if i + 1 < len(bucati_secundare) else ""
        if text_subpunct and len(text_subpunct) >= LUNGIME_MINIMA_CHUNK:
            # Construim un nume de articol nou, care arata clar din ce
            # sectiune originala provine, ex: "4.6.(1)"
            articol_nou = f"{c['articol']}({numar_subpunct})"
            chunks_finale.append({"articol": articol_nou, "text": text_subpunct})

chunks = chunks_finale
print(f"Chunk-uri mari splitate suplimentar dupa (1), (2), etc.: {numar_chunkuri_splitate}")
print(f"Total chunk-uri finale (dupa split secundar): {len(chunks)}")

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
# Verificam INTAI daca lista "chunks" are macar un element, inainte sa cautam
# maximul in ea -- altfel functia max() da eroare pe o lista goala.
if not chunks:
    print("\n!!! ATENTIE: 0 chunk-uri valide gasite. Regex-ul nu a prins niciun header.")
    print("Verifica manual textul din fisier -- poate documentul foloseste un")
    print("format de numerotare complet diferit, neacoperit inca de regex.")
else:
    chunk_lung = max(chunks, key=lambda c: len(c['text']))
    print(f"\n=== Chunk-ul cel mai lung: [{chunk_lung['articol']}] ({len(chunk_lung['text'])} caractere) ===")
    print("--- Inceput ---")
    print(chunk_lung['text'][:300])
    print("--- Sfarsit ---")
    print(chunk_lung['text'][-300:])

# --- Diagnostic: cautam in chunk-ul cel mai lung orice pattern posibil de header ratat ---
# Tot ce urmeaza ruleaza DOAR daca avem cel putin un chunk valid -- altfel
# n-are sens (si ar da eroare, la fel ca mai sus).
if chunks:
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