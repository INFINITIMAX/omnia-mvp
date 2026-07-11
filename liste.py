documente_normative = [
    {"nume": "P100", "an": 2013, "categorie": "seismic"},
    {"nume": "DTU", "an": 2018, "categorie": "instalatii"},
    {"nume": "NP112", "an": 2014, "categorie": "fundatii"},
    {"nume": "P118", "an": 2018, "categorie": "incendiu"}
]

for document in documente_normative:
    print(f"{document['nume']} ({document['an']}) — categorie: {document['categorie']}")