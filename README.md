# NormativAI (proiect intern „Omnia”)

Aplicație publică de întrebări-răspunsuri pe normative tehnice românești (construcții,
instalații), cu **răspunsuri bazate exclusiv pe dovezi citate** — niciun răspuns nu pleacă
fără cel puțin un fragment real, din documente aprobate explicit.

Live: https://normativai.ro (domeniu propriu; URL-ul Railway inițial, https://normativai-production.up.railway.app, rămâne activ)

## Cum funcționează

1. `POST /intreaba` primește întrebarea și aplică întâi controalele anonime (cookie
   semnat, quota, rate limit) — înainte de orice cost.
2. Un parser determinist (regex, fără LLM) caută o referință explicită de articol/document
   în text. Dacă există, e **exact lookup** direct în Postgres — fără Voyage.
3. Altfel, întrebarea primește un singur embedding Voyage (`voyage-3.5`) și e comparată
   prin pgvector cu fragmentele aprobate (top-5, prag de similaritate 0.50).
4. Dovezile găsite (deduplicate, limitate la ~12.000 caractere) sunt trimise lui Claude
   (`claude-sonnet-4-6`, max 800 tokeni) **doar dacă există cel puțin o dovadă** — fără
   dovezi, nu se apelează Claude deloc.
5. Răspunsul e validat: fiecare citare din text trebuie să corespundă unei dovezi
   efectiv trimise; identificatorii tehnici (ID intern, nume de fișier) nu ajung niciodată
   la client.

## Arhitectură

| Componentă | Rol |
|---|---|
| `main.py` | FastAPI: rute publice, orchestrare, control acces anonim, adaptoare lazy Voyage/Anthropic |
| `retrieval_core.py` | Parser articol/document, repository Postgres, logica exact/semantic — fără clienți externi |
| `generation_core.py` | Prompt + validare citări — pur, testabil fără Claude real |
| `access_control.py` | Cookie semnat, quota 10/browser, rate limit 5/min + 30/oră/IP, buget zilnic plătit |
| `procesare_documente.py` | Extragere text din PDF (PyMuPDF) |
| `glyph_mapping.py` | Reconstruiește formulele din PDF-uri cu fonturi CambriaMath fără `/ToUnicode` |
| `diacritice.py` | Normalizează sedilă→virgulă (ț/ș) simetric, la ingestie și la interogare |
| `populare_db.py` | Ingestion idempotent (hash de conținut) + embeddings pe loturi |
| `supabase/migrations/` | Schema versionată: RLS pe fiecare tabel, fără granturi publice |

## Securitate (verificat în cod, nu declarat)

- **RLS pe fiecare tabel**, activat + `revoke all ... from anon, authenticated` chiar în
  migrarea care îl creează — FastAPI e singurul client DB, deci nu există politici, doar
  deny-all pentru rolurile publice.
- Config **fail-closed**: orice variabilă de mediu lipsă sau malformată (chei de semnare,
  `ANONYMOUS_COOKIE_SECURE`, `TRUSTED_PROXY_HOPS`, buget zilnic) → 503, niciodată un
  fallback nesigur.
- CSP strict + `X-Frame-Options`, `Permissions-Policy` (blochează toți senzorii), HSTS.
- Zero `innerHTML`/`document.write` în frontend — randare exclusiv DOM/`textContent`,
  cu test static de regresie care interzice reintroducerea lor (textul vine din LLM și
  din documente, deci ar fi un vector XSS prin prompt injection).
- `X-Forwarded-For` citit corect (toate hop-urile, nu doar primul) — o breșă de spoofing
  găsită la review a fost remediată înainte de testarea externă.
- Buget zilnic de apeluri plătite (Voyage + Anthropic), rezervat pe conexiune separată
  ca să rămână corect chiar dacă restul cererii face rollback.
- `/docs`, `/redoc`, `/openapi.json` dezactivate în producție.
- Fără secrete în Git; `documente_noi/` (PDF-uri, text extras) e ignorat explicit.

## Pregătire locală

Python 3.11+.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Teste

```powershell
python -m pytest -q
```

419 teste, complet locale/mockuite — nu citesc `.env`, nu apelează Anthropic, Voyage sau
Supabase. Câteva zeci depind de `documente_noi/` (gitignored, date locale) și se sar automat
(`skip`) dacă nu există local.

## CI

La fiecare push/PR către `main`, GitHub Actions rulează automat (`.github/workflows/tests.yml`):

- toate testele (`python -m pytest -q`);
- `pip-audit` peste `requirements.txt`, ca să prindă vulnerabilități (CVE) cunoscute în
  dependențele fixate.

Dependabot (`.github/dependabot.yml`) verifică săptămânal dacă există actualizări pentru
dependențele Python. Totul rulează pe infrastructura gratuită GitHub Actions — fără costuri
și fără niciun secret configurat.

## Verificarea ingestion-ului fără cost

```powershell
python populare_db.py --dry-run
```

Validează metadata și chunking-ul (inclusiv gruparea în loturi pentru embeddings), fără
apeluri Voyage și fără să modifice Supabase.

## Pornire API local

Necesită variabile de mediu configurate local (vezi `main.py`: `DB_*`, `VOYAGE_API_KEY`,
`ANTHROPIC_API_KEY`, `ANONYMOUS_*`) — niciun secret nu intră în Git.

```powershell
python -m uvicorn main:app --reload
```

## Stare curentă (nu e un produs "terminat")

- **Live**, verificat end-to-end în producție: 6 documente aprobate, 3345 fragmente
  (verificare 03-09-2026).
- Normalizarea diacriticelor și gruparea embeddings-urilor pe loturi (batching) sunt gata
  și testate în `main`, dar reimportul real în Supabase (cost Voyage) nu a rulat încă.
- Rămân restante, cunoscut și asumat: testare externă controlată, ștergerea fizică
  automată a ferestrelor IP expirate (expiră logic, nu fizic, sub 24h), review de
  securitate independent final, lotul 4 de documente (P118/2, textul de bază — momentan
  există doar actul modificator).
- Quota anonimă e per-cookie de browser: ștergerea cookie-ului resetează limita — limitare
  MVP acceptată, nu o gaură necunoscută.

## Documentație suplimentară

- `PLAN.md` — obiectiv și etapele proiectului.
- `TASKS.md` — istoric de predare între sesiuni/agenți.
- `docs/HYBRID_SEARCH_SPEC.md` — contractul detaliat retrieval/API/teste.
- `docs/DECISIONS.md` — decizii explicite aprobate, cu motivare.
