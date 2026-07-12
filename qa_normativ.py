from dotenv import load_dotenv
import os
from anthropic import Anthropic

load_dotenv()
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

with open("normativ_1.txt", "r", encoding="utf-8") as fisier:
    continut_document = fisier.read()

def intreaba(intrebare):
    raspuns = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        system=f"""Esti un asistent care raspunde STRICT pe baza documentului de mai jos.

REGULI OBLIGATORII:
1. Raspunde DOAR pe baza informatiei gasite in document.
2. Citeaza EXACT articolul (numarul) din care provine raspunsul.
3. Daca informatia NU se gaseste in document, raspunde EXACT: "Nu am gasit aceasta informatie in document."
4. Nu inventa, nu presupune, nu completa cu cunostinte generale.

DOCUMENT:
{continut_document}""",
        messages=[
            {"role": "user", "content": intrebare}
        ]
    )
    return raspuns.content[0].text

# Teste
print("--- Intrebarea 1 ---")
print(intreaba("Cum se definesc starile limita conform STAS 10100/0?"))

print("\n--- Intrebarea 2 ---")
print(intreaba("Ce trebuie sa contina modelul de calcul?"))

print("\n--- Intrebarea 3 (capcana) ---")
print(intreaba("Care este distanta minima pentru amplasarea unei pompe de caldura?"))

print("\n--- Intrebarea 4 (capcana) ---")
print(intreaba("Ce culoare trebuie sa aiba fatada unei cladiri rezidentiale?"))

print("\n--- Intrebarea 5 (capcana subtila) ---")
print(intreaba("Ce spune articolul 3.3.3.9 despre stabilitate?"))

print("\n--- Intrebarea 6 (capcana reala) ---")
print(intreaba("Ce spune articolul 9.9.9 despre izolarea termica?"))