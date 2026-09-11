# Worker automat de ingestion PDF

## Avertisment actual — 09-09-2026: INACTIV, nu activați

Lucian a renunțat la activarea workerului. Codul este integrat (`6cfd69c`, PR8,
`origin/main` la `237e11d`), dar workerul rămâne **inactiv**, Task Scheduler este
**neinstalat**, iar `20260909000000_document_ingestion_sources.sql` este
**neaplicată conform predării**. Nu s-a făcut audit DB sau verificare scheduler nouă.
Codul, scriptul de înregistrare și migrarea se păstrează; nu se activează și nu se elimină.

**Fluxul curent aprobat:** Lucian pune **un PDF** în `documente_noi/_inbox`,
anunță Planner-ul și primește raport **local** de extracție/validare. DB + Voyage
necesită aprobare separată, iar publicarea prin status `approved` altă aprobare.
Importul manual sigur punctual **nu este încă livrat**; `populare_db.py` nu este
insert-only și nu trebuie prezentat drept substitut sigur al acestui flux.
Registrul SHA și pornirea la logon sunt decizii independente, neaprobate implicit
prin alegerea fluxului manual.

**Restul runbook-ului descrie comportamentul implementat, nu o operațiune activă.**
Comenzile de instalare/activare de mai jos sunt exclusiv **referință istorică**, nu
recomandare curentă și nu autorizație de execuție. Depunerea unui PDF nu pornește
un import automat în workflow-ul curent. Orice schimbare cere aprobare explicită nouă.

## Scop — referință istorică

Workerul local `auto_ingestion_worker.py` observă numai PDF-uri puse direct în
`documente_noi/_inbox/`. După instalarea inițială, operatorul nu rulează un CLI
zilnic: adaugă un PDF în acel folder, iar workerul îl procesează automat.

Workerul este **insert-only**: nu actualizează și nu șterge documente sau chunk-uri
existente. Un import reușit creează un document nou cu status
`indexed_pending_validation`; acesta nu poate fi folosit de aplicația publică până
la aprobarea explicită separată.

## Ce se întâmplă cu un PDF

1. Workerul așteaptă două scanări consecutive cu aceeași dimensiune și dată de
   modificare.
2. Verifică local antetul PDF, extrage textul și identifică deterministic codul,
   anul și titlul. Metadata ambiguă oprește fluxul înainte de DB sau Voyage.
3. Recalculează dimensiunea, data de modificare și SHA-256 după extracție. Dacă
   PDF-ul s-a schimbat în timpul procesării, îl marchează `unstable_pdf`, fără DB
   sau Voyage.
4. Deschide o tranzacție TLS, setează `statement_timeout` la 30 secunde și verifică
   hash-ul PDF plus identitatea documentului înainte de embeddings. Un duplicat sau
   conflict face rollback, fără scrieri noi, fără consum de buget și fără cost Voyage.
5. Numai pentru un PDF confirmat nou rezervă plafonul local, creează embeddings Voyage
   și inserează atomic documentul, identitatea PDF-ului și chunk-urile. O eroare face
   rollback DB; rezervarea rămâne consumată ca să nu existe retry automat cu cost.

Conexiunea PostgreSQL cere TLS (`sslmode=require`), are timeout de conectare de
10 secunde și timeout de query de 30 secunde. Voyage are timeout de 30 secunde și
zero retry-uri automate; orice indisponibilitate devine raport local `failed`, nu o
nouă cheltuială automată.

PDF-ul original nu este mutat, copiat sau modificat. Rapoartele locale fără text
normativ sunt în `documente_noi/_auto_state/`; ambele directoare rămân în afara
Git.

## Instalare unică pe Windows — referință istorică, neautorizată în fluxul curent

Instalarea Task Scheduler nu este executată de cod, test sau deploy. Lucian o
aprobă și o rulează separat, după ce migrarea versionată pentru
`document_ingestion_sources` a fost verificată și aplicată controlat în Supabase.

Din rădăcina repository-ului, într-un PowerShell al utilizatorului curent:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\register_auto_ingestion_worker.ps1 -Install
```

Scriptul refuză să modifice un task cu același nume și nu citește, afișează sau
primește secrete. El creează un task care pornește workerul la logon pentru
utilizatorul curent. Variabilele și cheile rămân exclusiv în `.env`, local și
neversionat; ele sunt citite numai de worker când rulează.

După instalare, utilizatorul doar pune PDF-uri noi în `_inbox`. Dacă Task Scheduler,
Python, folderul sau configurarea lipsesc, workerul nu poate porni și nu există
fallback web sau deploy Railway.

## Limite intenționate

- Nu există fallback LLM pentru metadata: un PDF neclar este refuzat, nu ghicit.
- Nu există aprobare automată sau acces public automat.
- Bugetul automat este fixat la **maximum 5 PDF-uri noi și 10.000 chunk-uri noi
  pe zi EET România** (`Europe/Bucharest`). Secțiunea locală de citire, validare
  și rescriere a `daily_budget.json` este protejată cu lock exclusiv inter-proces
  Windows (`msvcrt`) pe `daily_budget.lock`: pornirea accidentală a două instanțe
  nu poate rezerva de două ori ultimul slot. Lock indisponibil sau stare invalidă
  oprește importul fail-closed, înainte de Voyage. După validările locale, workerul
  verifică mai întâi în DB că documentul este nou, apoi rezervă plafonul, înainte de
  Voyage sau de orice `INSERT`. Duplicatele și conflictele nu consumă plafonul. La
  depășire, tranzacția de verificare face rollback fără `INSERT` și fără Voyage. Workerul
  scrie numai data locală `not_before_eet` pentru ziua EET următoare; până atunci, fiecare
  poll returnează `budget_deferred` înainte de extracție, DB sau Voyage. La ziua EET
  următoare, același PDF devine automat reeligibil.
- Un eșec tehnic este memorat local după SHA-256, ca să nu existe retry automat cu
  cost; un PDF schimbat primește hash nou și poate fi reevaluat.
- Migrarea Supabase și instalarea efectivă a Task Scheduler sunt gates manuale,
  separate, cu aprobare explicită.
