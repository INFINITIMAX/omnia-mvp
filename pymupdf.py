import fitz  # PyMuPDF

doc = fitz.open("NP0572002.pdf")
text_complet = ""

for pagina in doc:
    text_complet += pagina.get_text() + "\n"

with open("NP0572002_extras.txt", "w", encoding="utf-8") as fisier:
    fisier.write(text_complet)

print(f"Am extras {len(doc)} pagini, {len(text_complet)} caractere.")
