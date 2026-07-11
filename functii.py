documente_normative = [
    {"nume": "P100", "an": 2013, "categorie": "seismic"},
    {"nume": "DTU", "an": 2018, "categorie": "instalatii"},
    {"nume": "NP112", "an": 2014, "categorie": "fundatii"}
]

def cauta_document(nume_cautat, lista_documente):
    for document in lista_documente:
        if document["nume"] == nume_cautat:
            return document
    return "Documentul nu a fost gasit"

rezultat1 = cauta_document("DTU", documente_normative)
print(rezultat1)

rezultat2 = cauta_document("XYZ", documente_normative)
print(rezultat2)