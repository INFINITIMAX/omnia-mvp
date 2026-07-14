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