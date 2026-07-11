with open("document1.txt", "r", encoding="utf-8") as fisier:
    continut = fisier.read()

print(continut)

cuvinte = continut.split()
numar_cuvinte = len(cuvinte)

print(f"Documentul are {numar_cuvinte} cuvinte")