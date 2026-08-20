# OMNIA — Context complet de proiect

> Acest fișier e menit să dea unui asistent AI (Claude Code) context maxim despre proiectul Omnia: ce este, ce s-a construit până acum, ce decizii au fost luate și de ce, și încotro se îndreaptă. Se recomandă redenumirea/plasarea acestui fișier ca `CLAUDE.md` în rădăcina repo-ului `omnia-mvp`, astfel încât Claude Code să-l citească automat la fiecare sesiune.

---

## 1. Cine sunt eu (Lucian) și cum vreau să lucrez

- Sunt co-fondator și manager la **360ERA**, o companie românească specializată în tururi virtuale interactive 360° pentru imobiliare (agenții, dezvoltatori, design interior). Partenerul meu de afaceri e **Andrei**.
- Dezvolt independent **Omnia**, sub contul GitHub **INFINITIMAX**, în repo-ul **`omnia-mvp`**.
- **Învăț Python de la zero**, în paralel cu construirea Omnia. Orice cod scris pentru mine trebuie explicat **linie cu linie**: scop, sintaxă Python, metodologie — nivel de începător.
- Prefer **sesiuni de lucru tip sprint**, cu **un singur obiectiv clar** pe sesiune, nu multitasking pe mai multe direcții deodată.
- Corectez rapid presupunerile greșite — dacă asistentul înțelege greșit ceva, o spun imediat și vreau să se recalibreze, nu să continue pe direcția greșită.
- Comunic informal, în română (uneori în engleză din cauza speech-to-text).

## 2. De ce există Omnia — cele două obiective simultane

Omnia nu e doar un produs. Are **două scopuri paralele, la fel de importante**:

1. **Produs vandabil și funcțional** — un AI copilot pentru conformitate tehnică în construcțiile din România, care poate fi folosit real de colegi/clienți.
2. **Acumulare de skill-uri pentru angajare** — vreau să pot aplica la joburi în AI/automation în ~2-3 luni. De asta, orice decizie tehnică care are și valoare de CV (OOP, teste automate, deployment cloud, FastAPI, arhitectură RAG, agenți AI) trebuie semnalată explicit ca atare, nu doar tratată ca "ce rezolvă problema cel mai repede".

Principiul central al produsului: **"niciun răspuns fără dovadă"** — Omnia nu răspunde niciodată fără citare exactă din documentul normativ sursă.

## 3. Ce este Omnia, concret

Un RAG (Retrieval-Augmented Generation) system care:
- indexează documente normative din construcții românești (normative tehnice, coduri de proiectare etc.)
- răspunde la întrebări cu **citare obligatorie** a articolului/sursei
- detectează **conflicte** între documente diferite
- combină **căutare semantică** (embeddings) cu **căutare exactă SQL** (pentru "arată-mi articolul X")

Target MVP: **10-20 documente legislative**, calitate maximă, nu cantitate.

## 4. Arhitectura tehnică actuală

### Stack
- **Python** (limbaj principal, învățat de la zero pe parcurs)
- **PostgreSQL + pgvector** — bază de date vectorială pentru embeddings
- **Voyage AI** — provider de embeddings
- **Claude API (Anthropic)** — generare răspunsuri, cu prompting care impune citare obligatorie
- **FastAPI + HTML** — interfață web plănuită, pentru testare cu colegii
- Migrare plănuită: **pgAdmin → Supabase**

### Pipeline de chunking (componenta cea mai lucrată)
Fișierul cheie: `populare_db.py`, care integrează logica din `chunkingv2.py`:
- regex cu pattern `{0,4}` pentru identificarea numerotării articolelor
- suport pentru **2 nivele de headere**
- detecție automată a **cuprinsului** (limitată la primele 20% din document, ca să nu confunde alte liste numerotate cu cuprinsul real)
- **deduplicare**, păstrând varianta mai lungă când există duplicate
- **split secundar** pe marcaje `(1)/(2)` pentru chunk-uri care depășesc 2000 de caractere

**De ce regex și nu AI pentru chunking (decizie arhitecturală importantă):**
Documentele normative românești au formate de numerotare foarte variate — asta e o **limitare cunoscută** a abordării actuale, documentată explicit în `NOTES.md`. Am decis să rămân pe regex acum și să amân **chunking agentic** (AI care detectează stilul de numerotare per document) pentru mai târziu, **după ce acumulez experiență cu agenți** (vezi Proiect 2 mai jos) — nu are sens să construiesc agenți complecși înainte să înțeleg bine cum se comportă.

### Verificare
`verifica_db.py` — script de testare/validare a bazei de date, construit și testat.

### Documente
NP010 a fost adăugat recent la lista de documente procesate.

### De ce hybrid search e obligatoriu (decizie arhitecturală)
Căutarea semantică pură **nu poate răspunde fiabil** la cereri de tipul "arată-mi articolul X" — de asta a fost nevoie de căutare SQL exactă în paralel cu cea semantică, plus **exhaustive threshold-based search** cu detecție de conflicte.

### Ce a fost amânat intenționat și de ce
- **Generare de scheme CAD prin AI** — amânată pentru v2.0+, din cauza **riscului de răspundere legală** dacă AI-ul greșește o schemă tehnică folosită real într-un proiect de construcție.
- **Crawler pentru monitorizarea automată a documentelor noi** — depriorizat în favoarea încărcării manuale, cel puțin pentru MVP.

## 5. Progres realizat (stadiile 1-4 din roadmap-ul inițial — COMPLETE)

- Instalare Python, VS Code, configurare Git/GitHub
- Integrare Claude API cu prompting care impune citare obligatorie
- Integrare Voyage AI pentru embeddings
- PostgreSQL cu pgvector
- Căutare semantică cross-document
- Căutare exactă SQL pe articol
- Exhaustive threshold-based search cu detecție de conflicte
- Interfață interactivă de terminal (funcțională, pre-FastAPI)
- Pipeline de chunking v2 (descris mai sus) — funcțional pe mai multe documente normative
- `verifica_db.py` — testat

## 6. Roadmap complet — toate proiectele și de ce sunt în această ordine

### Proiect 1 — Omnia MVP (PRIORITATE ZERO, în lucru acum)
10-20 documente, citare obligatorie, detecție conflicte, hybrid search, interfață FastAPI+HTML pentru testare internă cu colegii.

### Proiect 2 — Agent de job-matching
- Extracție de skill-uri din CV
- Matrice de scoring ponderată
- Ponderile sunt **asignate de AI**, în funcție de limbaj "required" vs. "nice to have" din anunțul de job
- Job description-ul se lipește manual (fără scraping automat, cel puțin inițial)
- **De ce e Proiect 2 și nu Proiect 1:** e concepută explicit ca prima experiență practică cu agenți AI, înainte de a aplica agenți pe lucruri mai riscante (ex: chunking agentic pe Omnia)

### Proiect 3 — Omnia cu conștientizare de context al clădirii
Extensie a MVP-ului, condiționată de finalizarea Proiectului 1.

### Proiect 4 — Selecție automată de scheme tehnice AutoCAD
Dintr-o bază de date de ~100 PDF-uri.

### Itemi viitori, fără tracking activ momentan
- **Chunking agentic** — înlocuirea regex-ului cu agenți AI care detectează stilul de numerotare per document. Planificat **după** experiența cu agenți din Proiectul 2.
- **Orchestrare multi-agent** — a doua iterație a Proiectului 2, după ce Proiectul 2 de bază funcționează.

## 7. Alte lucrări conexe (context, nu parte din Omnia direct)

- CV generat în stilul LaTeX "Jake's Resume Template", acoperind experiența din 2020, Master în Smart Cities + diplomă de inginer în Hidroenergetică (Politehnica București), autorizație ANRE de electrician, competențe tehnice separate pe unelte de proiectare vs. unelte AI/dezvoltare software.
  - **Problemă nerezolvată, neprioritară:** diacriticele românești (ș/ț) se stricau la extracția ATS din PDF. Lăsată neremediată — CV-ul nu e prioritate imediată.
- Studiu OpenAI API / curs DataCamp Associate AI Engineer: structura chat completions, `temperature`, `finish_reason`, f-strings, chain-of-thought prompting.
- Anunț de job la Vodafone AI analizat față de competențele mele: **gap-uri** (deep learning frameworks, platforme cloud, OOP/design patterns), **puncte forte** (RAG/NLP aplicat, PostgreSQL, leadership antreprenorial).

## 8. Context 360ERA (compania, nu Omnia — separat, dar relevant ca fundal)

- Template-uri HTML de email în Brevo, estetică "dark luxury": `#080808` fundal, `#c9a84c` accente aurii, font Georgia serif
- Ghid HTML "Kit de valorificare" pentru clienți
- Script de cold-call pentru companii de mobilă
- CRM în Airtable
- Website `360era.ro`, construit de la zero, cu secțiuni pe audiențe (dezvoltatori, agenții, designeri de interior)
- Lucru cu Blender MCP: sisteme de materiale, `KHR_materials_variants` (BAZA/CALD) pentru export GLB către 3DVista, iluminat LED, separare de mesh-uri, HDRI world lighting (regulă fixă: **HDRI-ul panoramic nu se modifică niciodată, doar luminile din scenă**)
- Pipeline de procesare imagini panoramice: upscaling FSRCNN x4 cu procesare pe tile-uri, unsharp masking
- Workflow Photoshop → 3DVista pentru transparențe
- Tool de status floor plan (desenare poligoane, overlay culoare pe disponibilitate)
- Tool web interactiv de floor plan (`complex-final.html`) cu secțiune CONFIG pentru personalizare per client, folosit în pitch-uri către dezvoltatori imobiliari
- Blender MCP — istoric mai vechi: troubleshooting conexiune MCP (necesar Python 3.12 via flag `--python 3.12`, din cauza incompatibilității `pyiceberg` cu Python 3.14), lucru cu scene importate din IFC (obiecte FOCICA), materiale PBR, props decorative, UV unwrapping manual pentru importuri OBJ
- Produs inițial 360ERA: portal de agenți pe Google Sheets pentru actualizare prețuri, tool-uri de floor plan interactiv — a stabilit abordarea tehnică de bază a companiei: unelte HTML/JS ușoare, embedded în tururi 3DVista

## 9. De ce încep acum experimente cu Claude Code (context al acestei tranziții)

- Iau o pauză de câteva zile de la Omnia ca produs, ca să învăț **Claude Code** separat, fără presiunea de livrare.
- Obiectiv: să înțeleg bine Claude Code single-agent (plan mode, `CLAUDE.md`, permisiuni), apoi să explorez orchestrare cu **2-4 agenți simultan** (probabil via `git worktree`, eventual Agent Teams experimental sau orchestratori externi tip Multiclaude).
- Autentificare: **cheie API din Anthropic Console**, NU abonament Pro/Max — am deja cont de Console cu credite, folosit pentru Omnia.
- **Decizie luată:** cheie API separată pentru experimentele cu Claude Code, distinctă de cheia folosită de Omnia în producție — pentru tracking curat al costurilor și izolare de securitate (dacă o cheie se scurge accidental într-un commit, blast radius-ul e limitat).

## 10. Cum vreau să lucreze Claude Code cu mine — reguli explicite

Astea sunt instrucțiuni de comportament, nu doar context:

1. **Explică orice cod linie cu linie** — scop, sintaxă, metodologie, nivel de începător. Sunt la început cu Python.
2. **Flag explicit** când un concept/decizie tehnică are și valoare de CV/angajare (OOP, teste automate, deployment cloud, FastAPI, design de agenți) — nu doar valoare funcțională pentru produs.
3. **Nu auto-accepta edit-uri de fișiere.** Vreau să revizuiesc fiecare modificare înainte de a fi aplicată — configurează permisiunile să NU fie pe auto-accept.
4. **Un obiectiv clar per sesiune.** Nu sări între mai multe direcții în aceeași sesiune fără să fie discutat explicit.
5. **Corectează rapid dacă greșesc o presupunere** — nu continua pe o direcție pe care tocmai am corectat-o.

## 11. Ce urmează imediat

- Confirmare `ANTHROPIC_API_KEY` (cheie nouă, dedicată Claude Code) setată corect în Windows
- Instalare Claude Code (`irm https://claude.ai/install.ps1 | iex`)
- Sesiuni introductive de familiarizare cu Claude Code (fără presiune de livrare pe Omnia)
- După familiarizare: prima experiență de paralelizare cu `git worktree` + 2-3 sesiuni Claude Code simultane, pe task-uri independente