import pdfplumber

with pdfplumber.open("normativ_mare.pdf") as pdf:
    text_complet = ""
    for pagina in pdf.pages:
        text_pagina = pagina.extract_text()
        if text_pagina:
            text_complet += text_pagina + "\n"

with open("normativ_mare.txt", "w", encoding="utf-8") as fisier:
    fisier.write(text_complet)

print(f"Am extras {len(pdf.pages)} pagini, {len(text_complet)} caractere.")