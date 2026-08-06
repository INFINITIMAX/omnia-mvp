# Note de arhitectura - Omnia

## Chunking (Etapa 2)

**Problema identificata (Sesiunea 12):**
Regex-ul simplu folosit acum (`\d+\.\d+\.\d+`) functioneaza doar pentru numerotare de tip "3.1.3.2". 
Normativele reale au formate diferite de numerotare:
- Cifre cu puncte: 3.2.2
- Litera + cifra: G.2
- Litera simpla: c) sau (c)
- Cuvant + numar: Art. 15
- Numerotare romana + text: Cap. IV, Sectiunea 2

**Solutii posibile pentru mai tarziu:**
1. Chunking adaptiv per format de document (regex diferit per stil identificat)
2. Chunking semantic cu AI (Claude imparte documentul in unitati logice, indiferent de numerotare) - mai robust, dar mai costisitor

**Decizie actuala:** 
Pentru MVP (Etapa 2-4), regex simplu per document, verificat manual. 
Solutia robusta se implementeaza abia in Etapa 5 (crawler automat, scala mare), cand nu mai putem verifica manual fiecare document.

**Alta observatie:** chunking-ul actual trateaza toate nivelurile ierarhice (capitol, subcapitol, sub-subcapitol) ca fiind egale, fara relatie parinte-copil. Nu e problema pentru cautare simpla, dar ar putea conta pentru afisarea contextului complet sau detectarea de conflicte (Etapa 4). Solutie posibila: camp "parinte" calculat din numarul articolului.

## Cautare (Etapa 2-3)

**Observatie (Sesiunea 20):** cautarea semantica (embeddings) nu functioneaza bine pentru interogari de tip "da-mi articolul X" (cautare exacta dupa identificator). Functioneaza bine doar pentru intrebari despre CONTINUT/sens.

**Solutie posibila pentru mai tarziu:** daca vrem sa suportam si cautare exacta dupa numar de articol, avem nevoie de un mecanism separat (cautare SQL directa dupa coloana "articol", nu prin embeddings) - un fel de "hybrid search" (semantic + exact match).

## Cautare - de revizuit la scara mai mare (dupa Sesiunea 20)

Motorul de cautare (embeddings + prag similaritate) functioneaza bine la scara mica (2 documente, 46 chunks), testat manual. 
De revenit cu testare riguroasa (recall/precizie, prag adaptiv, indexare HNSW) cand baza de date creste semnificativ (Etapa 5, zeci de documente).

## Sesiune [azi] — Validare pipeline RAG pe document real (60 pagini)

- Regex de chunking extins la 3 tipare: articole cu literă (3.2.(A).), 
  ANEXA (bibliografie), articole cu cifre multiple fara paranteza (cap. 3.3).
- Cuprins eliminat automat inainte de chunking (cauta ultima linie de tip "titlu....123").
- Chunk-uri junk (<15 caractere) filtrate.
- Rezultat: document NP0572002 (60 pagini) -> 307 chunk-uri curate, 
  cel mai lung chunk redus de la 47.651 la 4.568 caractere.
- Testat Q&A cu 3 intrebari reale -> 3/3 corecte, citare exacta (dupa fix de prag).
- Prag de similaritate (cauta_exhaustiv) coborat de la 0.6 la 0.5 -> 0.6 era 
  prea strict pentru text tehnic normativ (scoruri naturale mai mici decat 
  la text conversational). Validat cu date reale (verifica_similaritate.py).
- Lectie: daca modifici cod cat timp un proces Python vechi ruleaza (bucla 
  while True), schimbarile nu se aplica -> repornire completa necesara.

### Urmatorii pasi (plan stabilit)
1. ~~Testare Q&A pe document real~~ ✅ DONE
2. Generalizare script extragere (fisier hardcodat -> parametru)
3. Incarcare restul de 9 normative
4. Backend FastAPI (endpoint POST /intreaba)
5. Frontend HTML simplu, pentru testare cu colegii