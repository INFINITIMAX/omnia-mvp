from dotenv import load_dotenv
import os
import voyageai

load_dotenv()
vo = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))

texte = ["Pompa de caldura trebuie amplasata la minim 3 metri", "Distanta minima pentru echipamente de incalzire"]

rezultat = vo.embed(texte, model="voyage-3.5", input_type="document")

print(f"Numar de embeddings: {len(rezultat.embeddings)}")
print(f"Dimensiune embedding: {len(rezultat.embeddings[0])}")
print(f"Primele 5 numere din primul embedding: {rezultat.embeddings[0][:5]}")