import fitz  # PyMuPDF
import os
import glob

# ============================================================
# Acest script scaneaza SINGUR un folder, gaseste toate PDF-urile,
# si extrage textul din cele care NU au fost deja procesate.
# Tu doar pui PDF-uri noi in folderul "documente_noi", fara sa
# mai tastezi tu manual numele fiecaruia.
# ============================================================

FOLDER_DOCUMENTE = "documente_noi"

# glob.glob() cauta fisiere dupa un tipar (pattern), ca un "Find" automat.
# os.path.join() lipeste corect calea catre folder + tiparul de cautare,
# indiferent daca esti pe Windows sau Mac/Linux (ei folosesc simboluri
# diferite pentru desparfirea folderelor: \ pe Windows, / pe Mac/Linux,
# iar os.path.join() alege automat pe cel corect).
tipar_cautare = os.path.join(FOLDER_DOCUMENTE, "*.pdf")
lista_pdf_uri = glob.glob(tipar_cautare)

print(f"Am gasit {len(lista_pdf_uri)} fisiere PDF in folderul '{FOLDER_DOCUMENTE}'.")

# Contoare, ca sa stim la final cate am procesat si cate am sarit
procesate = 0
sarite = 0

# "for nume_pdf in lista_pdf_uri:" inseamna: ia pe rand fiecare element
# din lista, il pune temporar in variabila "nume_pdf", si ruleaza tot
# blocul indentat de mai jos pentru el, apoi trece la urmatorul.
for nume_pdf in lista_pdf_uri:

    # os.path.splitext() taie un nume de fisier in 2 bucati: (nume, extensie)
    # ex: "documente_noi/NP065.pdf" -> ("documente_noi/NP065", ".pdf")
    # [0] ia doar prima bucata din acel tuplu (numele, fara extensie)
    nume_baza = os.path.splitext(nume_pdf)[0]
    nume_output = f"{nume_baza}_extras.txt"

    # os.path.exists() verifica daca un fisier chiar exista pe disc.
    # Daca fisierul _extras.txt exista deja, inseamna ca am procesat
    # deja acest PDF intr-o rulare anterioara -> il sarim, ca sa nu
    # facem munca (si apeluri catre Voyage, mai tarziu) de doua ori degeaba.
    if os.path.exists(nume_output):
        print(f"  SARIT (deja procesat): {nume_pdf}")
        sarite += 1
        continue  # "continue" opreste bucla curenta si trece direct la urmatorul element

    # Abia daca fisierul NU a fost procesat inainte, facem extragerea reala
    doc = fitz.open(nume_pdf)
    text_complet = ""

    for pagina in doc:
        text_complet += pagina.get_text() + "\n"

    with open(nume_output, "w", encoding="utf-8") as fisier:
        fisier.write(text_complet)

    print(f"  PROCESAT: {nume_pdf} -> {len(doc)} pagini, {len(text_complet)} caractere")
    procesate += 1

print(f"\nGata. Procesate: {procesate}, sarite (deja existente): {sarite}")