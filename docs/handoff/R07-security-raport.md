# R07 — audit securitate release — raport

Executat: 25-09-2026. Read-only strict: nicio comandă de scriere, deploy, DB write sau apel plătit. Domeniu: brief `R07-security.md`.

## Verdict: **PASS** (condiționat)

Codul static nu are găuri de securitate identificabile pentru profilul de produs actual (tool public anonim, cu quotă/rate-limit, fără date personale sensibile colectate). Verdictul e condiționat de câteva puncte care nu pot fi confirmate static (vezi §4).

## 1. Endpoint-uri (main.py, singurul fișier cu rute HTTP)

| Rută | Metodă | Expunere |
|---|---|---|
| `/` | GET | pagina publică (index.html) |
| `/health` | GET | healthcheck public, fără date sensibile |
| `/termeni`, `/confidentialitate` | GET | pagini statice publice |
| `/intreaba` | POST | singurul endpoint costisitor (Voyage+Anthropic), protejat de quotă+rate-limit |

`docs_url=None, redoc_url=None, openapi_url=None` (main.py:344) — documentația OpenAPI e dezactivată, corect pentru producție. **Nicio rută de admin/debug/ingestion nu e expusă public** — scripturile de ingestie (`auto_ingestion_worker.py`, `manual_ingestion_import.py`) sunt CLI-uri separate, nu rute HTTP.

## 2. Autentificare/autorizare

Nu există login/sesiune de utilizator — intenționat, produsul e un tool public anonim de întrebări. Controlul de acces e prin cookie anonim semnat HMAC (`access_control.py`), nu prin identitate reală. Corect pentru acest profil de produs, nu un gap.

## 3. Rate limiting — solid, verificat direct în cod

`access_control.py` implementează:
- Quotă per-vizitator: 10 întrebări (`ANONYMOUS_QUOTA_LIMIT`), aplicată prin `UPDATE ... WHERE questions_used < %s` — atomic la nivel DB.
- Rate limit per-IP (hash HMAC, nu IP brut stocat): 5/minut, 30/oră, ferestre UTC, `pg_advisory_xact_lock` per hash pentru atomicitate (access_control.py:243-275).
- Plafon zilnic global pentru apeluri plătite (Voyage+Anthropic): `DEFAULT_DAILY_PAID_CALL_LIMIT = 200`, suprascris prin `DAILY_PAID_CALL_LIMIT` (env).
- Toate căile sunt fail-closed: config invalid → `ValueError` la pornire (`__post_init__`), rezultat rate-limit incoerent → `ServiceDependencyError`.

Acesta e exact mecanismul care protejează costul — nu doar abuzul, ci și bugetul lunar Anthropic/Voyage.

## 4. CORS

**Nicio middleware CORS configurată** (`grep CORSMiddleware/allow_origins` → zero rezultate în afara `access_control.py`, care e cu totul altceva). Verificat: front-end-ul e servit same-origin de `main.py` prin `StaticFiles` (`static/index.html` etc.), deci nu există niciun consumator cross-origin legitim. Absența CORS = fail-closed implicit (browserele blochează citirea cross-origin fără header). **Nu e un gap**, e comportamentul corect pentru arhitectura same-origin curentă.

## 5. Secrete/logging

- Toate secretele vin din variabile de mediu prin `_required_environment()` (main.py:253-257) — `VOYAGE_API_KEY`, `ANTHROPIC_API_KEY`, `DB_HOST/NAME/USER/PASSWORD/PORT`, `ANONYMOUS_COOKIE_SIGNING_KEY`, `ANONYMOUS_IP_HASH_KEY`. Lipsă → `DependencyConfigurationError`, nu crash cu valoare goală.
- `.env` e în `.gitignore` (`.env`, `*.env`) și **confirmat netracked** (`git ls-files | grep .env` → gol).
- Niciun `print`/`log` lângă variabile cu `key`/`secret`/`token`/`password` în `main.py` (grep țintit → zero rezultate).
- Handler-ul de erori (main.py:796-808) loghează **doar** `type(error).__name__` + un cod stabil pentru `GenerationValidationError` — exact contractul D21 deja aprobat. `psycopg2.Error` e prins dar nu logat cu detalii (connection string, query) — bun, nu scurge topologia DB.
- Cookie-ul anonim: `HttpOnly`, `SameSite=Lax`, `secure` condiționat de `runtime_config.cookie_secure` (main.py:422-431) — corect, dar depinde ca `ANONYMOUS_COOKIE_SECURE` să fie setat corect în producție (nu poate fi verificat static).

## 6. Acces DB

`_open_db_connection()` (main.py:260-268) face `psycopg2.connect` direct cu `DB_HOST/NAME/USER/PASSWORD/PORT` din env — conexiune Postgres directă (probabil connection string Supabase), nu prin client SDK Supabase cu anon/service-role key. **Nu pot verifica static**: ce rol/privilegii are `DB_USER` (least-privilege vs. superuser), și dacă RLS (row-level security) e activat pe tabelele Supabase — astea sunt setări DB live, nu în cod.

## 7. Rute administrative

Nu există. Singurele scripturi cu putere de scriere (`auto_ingestion_worker.py`, `manual_ingestion_import.py`, `backup_baza_de_date.py`, `cleanup_rate_limit_buckets.py`) sunt CLI-uri rulate manual/cron, nu expuse ca rute HTTP.

## Necesită verificare externă (nu poate fi confirmat static)

1. **Rolul `DB_USER` în Supabase** — are exact privilegiile necesare (SELECT/INSERT pe tabelele relevante), sau e un rol prea larg (owner/superuser)? RLS activat?
2. **`ANONYMOUS_COOKIE_SECURE`** — valoarea reală setată pe Railway (trebuie `true` în producție HTTPS).
3. **Valorile reale ale secretelor** (lungime/entropie) — codul impune minim 32 octeți și verifică slăbiciunea (`_require_secret`), dar valoarea efectivă din Railway env nu poate fi citită de aici.
4. Dependabot are un PR deschis pentru `anthropic` 0.116.0→1.3.0 (semnalat deja în HANDOFF.md) — schimbare majoră, nu am evaluat aici dacă introduce implicații de securitate (ex. schimbări de auth în SDK); merită o trecere separată la review.

## Rezumat priorități

- **Critic:** niciunul găsit.
- **Mediu:** niciunul găsit din cod; cele 3 puncte de la §"necesită verificare externă" (1-3) ar trebui bifate manual o dată, nu sunt findinguri de cod.
- **Minor:** niciunul.
