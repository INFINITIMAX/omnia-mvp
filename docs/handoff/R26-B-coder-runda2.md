# R26-B — Runda 2 (planner, 29-09-2026)

Rulare planner cu manifestele tale — ambele se opresc (fail-closed, corect):

1. **P 118/2**: `ValueError: itemul 24: nu conține nici „cuprins:”, nici propoziția „se abrogă.”`. Itemul 24 (ordin, rândurile 397–400): „La tabelele 7.10—7.12, sintagma „Valorile minime de calcul al densității (intensității) de stropire” se înlocuiește cu sintagma „Valorile minime de calcul al densității (intensității) de stingere”.”
   → Adaugă tipul `inlocuieste_sintagma_in_bloc`: segmentarea recunoaște itemii „… sintagma „X” se înlocuiește cu sintagma „Y”.” (X și Y extrase din instrucțiune, verificate literal în ordin); manifestul dă `ancora_inceput`/`ancora_sfarsit` (ca la `inlocuieste_bloc`, de la tabelul 7.10 până după tabelul 7.12); în bloc, X se înlocuiește cu Y (tolerant la rupturi de rând), numărul de înlocuiri ≥1 și raportat; fără marcaj per apariție (ca înlocuirile globale), dar raportat. Citește baza.txt în jurul tabelelor 7.10–7.12 ca să alegi ancorele și scoate `manual: true`.
2. **P 118/3**: operația 8 (`3.8.2.5`, alineat `1`): `marcajul /\(1\)/ are 0 potriviri în regiune`. În bază: `3.8.2.5 (1)Sunetul alarmei…` — primul alineat e pe **rândul punctului**, imediat după număr, uneori fără spațiu după `)`. La fel `5.3.5 (1)Cablurile…`, `3.3.1 (1) Echiparea…`.
   → Localizarea subunității trebuie să accepte, pentru prima subunitate, poziția de după numărul punctului pe rândul de titlu (cu sau fără spațiu după `)`/`)`). Păstrează regula „exact o potrivire”. Verifică și literele (`a)`) în aceeași situație.
3. După corecturi, recitește toate operațiile din ambele manifeste împotriva bazei pentru aceeași clasă de problemă (prima subunitate pe rândul punctului) și raportează ce ai verificat.

Constrângeri neschimbate (vezi `R26-B-coder.md`). Adaugă „Runda 2” în `R26-B-coder-raport.md`.
