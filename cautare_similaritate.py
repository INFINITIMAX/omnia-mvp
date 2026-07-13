from dotenv import load_dotenv
import os
import voyageai
import numpy as np

load_dotenv()
vo = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))

# Cateva "chunk-uri" de test (poti folosi cele din documentul tau normativ)
documente = [
    "Starile limita se definesc in conformitate cu STAS 10100/0 si se impart in doua categorii.",
    "Verificarea satisfacerii cerintei de rezistenta si stabilitate se face pe conceptul de stari limita.",
    "Modelul de calcul trebuie sa fie suficient de precis pentru a estima comportarea cladirii.",
]

# Cream embeddings pentru toate documentele
embeddings_documente = vo.embed(documente, model="voyage-3.5", input_type="document").embeddings

# Intrebarea utilizatorului
intrebare = "Cum sunt clasificate starile limita?"
embedding_intrebare = vo.embed([intrebare], model="voyage-3.5", input_type="query").embeddings[0]

# Calculam similaritatea cosinus intre intrebare si fiecare document
def similaritate_cosinus(a, b):
    a = np.array(a)
    b = np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

scoruri = []
for i, emb_doc in enumerate(embeddings_documente):
    scor = similaritate_cosinus(embedding_intrebare, emb_doc)
    scoruri.append((scor, documente[i]))

# Sortam dupa cel mai relevant
scoruri.sort(reverse=True)

print(f"Intrebare: {intrebare}\n")
for scor, text in scoruri:
    print(f"Scor: {scor:.4f} -- {text}")