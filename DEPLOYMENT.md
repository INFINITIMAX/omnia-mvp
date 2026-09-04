# DEPLOYMENT — NormativAI (Omnia)

Acest document descrie **numai** configurația necesară rulării backend-ului în producție.
Nu conține și nu trebuie să conțină vreo valoare reală, cheie, parolă sau exemplu care
seamănă cu un secret. Valorile reale se introduc exclusiv în panoul de variabile al
platformei de hosting, niciodată în repo.

## 1. Procesul aplicației

Comanda de pornire este deja în `Procfile`:

```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

`PORT` este furnizat automat de Railway; nu îl seta manual.

## 2. Healthcheck

Healthcheck-ul platformei trebuie configurat pe:

```
/health
```

Endpoint-ul este public, nu cere autentificare, nu deschide conexiuni la baza de date, nu
apelează Voyage sau Anthropic și nu citește configurația anonimă. Returnează `200` cu
`{"status": "ok"}`. Un incident tranzitoriu de bază de date **nu** trebuie să oprească
containerul, de aceea healthcheck-ul este deliberat superficial.

## 3. Variabile de mediu obligatorii

### 3.1 Bază de date (Supabase / PostgreSQL)

| Variabilă | Rol |
| --- | --- |
| `DB_HOST` | Numele de gazdă al serverului PostgreSQL al proiectului Supabase. |
| `DB_NAME` | Numele bazei de date folosite de aplicație. |
| `DB_USER` | Utilizatorul de aplicație cu care se conectează backend-ul. |
| `DB_PASSWORD` | Parola utilizatorului de mai sus. **Secret.** |
| `DB_PORT` | Portul serverului PostgreSQL. |

Toate cinci sunt citite abia în timpul unei cereri, nu la import. Dacă oricare lipsește sau
este goală, cererea răspunde cu `503` generic, fără detalii interne.

### 3.2 Furnizori externi

| Variabilă | Rol |
| --- | --- |
| `VOYAGE_API_KEY` | Cheia API pentru embedding-ul întrebării (căutarea semantică). **Secret.** |
| `ANTHROPIC_API_KEY` | Cheia API pentru generarea răspunsului din dovezile recuperate. **Secret.** |

Clienții HTTP se creează lazy, doar când ramura respectivă chiar are nevoie de ei, deci o
cheie lipsă nu blochează pornirea procesului, ci produce `503` la cererea afectată.

### 3.3 Controale anonime

| Variabilă | Rol |
| --- | --- |
| `ANONYMOUS_COOKIE_SIGNING_KEY` | Cheia server-side care semnează HMAC cookie-ul anonim `normativai_anon` și derivă `visitor_hash`. **Secret.** Minimum 32 de octeți aleatori. |
| `ANONYMOUS_IP_HASH_KEY` | Cheia server-side, **diferită** de cea de mai sus, folosită pentru hash-ul HMAC al adresei IP din rate limiting. **Secret.** Minimum 32 de octeți aleatori. |
| `ANONYMOUS_COOKIE_SECURE` | Acceptă strict `true` sau `false` (case-insensitive, cu spații ignorate). În producție, pe HTTPS, se setează `true`, ca să adauge atributul `Secure` cookie-ului. Orice altă valoare, sau lipsa variabilei, produce `503` generic. |

Cele două chei trebuie să fie distincte; altfel configurația este respinsă și cererile
răspund `503`.

**Valoarea pentru Railway:** `ANONYMOUS_COOKIE_SECURE=true`.

### 3.4 Proxy de încredere

| Variabilă | Rol |
| --- | --- |
| `TRUSTED_PROXY_HOPS` | Numărul de proxy-uri de încredere aflate în fața aplicației. Întreg nenegativ, implicit `0`. |

Semantica, pe scurt:

- `0` (implicit): se folosește exclusiv adresa conexiunii TCP (`request.client.host`);
  antetul `X-Forwarded-For` este ignorat complet.
- `N > 0`: se ia al **N**-lea element numărând **de la dreapta** din `X-Forwarded-For`,
  pentru că numai acele poziții sunt scrise de infrastructura proprie. Cu `N` setat corect,
  elementele din stânga sunt controlate de client și nu sunt folosite.
- Toate antetele `X-Forwarded-For` primite sunt unite în ordinea sosirii înainte de
  împărțirea pe virgulă. Un proxy care adaugă un antet separat, în loc să extindă valoarea
  existentă, nu poate face aplicația să citească doar antetul clientului.
- Dacă antetul lipsește, are mai puține elemente decât `N`, sau elementul selectat nu este
  o adresă IP literală validă, se cade înapoi pe `request.client.host`. Nu se acceptă
  niciodată o valoare neverificată.
- O valoare care nu este un întreg nenegativ produce `503` generic la pornirea cererii,
  la fel ca orice altă configurație invalidă.

**Valoarea pentru Railway:** `TRUSTED_PROXY_HOPS=1`.

Fără această setare, în spatele proxy-ului Railway toți vizitatorii ar împărți un singur
bucket de rate limit (5 cereri/minut și 30/oră **în total**, pentru toată lumea), pentru că
`request.client.host` ar fi adresa proxy-ului, nu a vizitatorului.

### ⚠️ Supraevaluarea lui `N` este o breșă de securitate, nu o imprecizie

`N` trebuie să fie **exact** numărul de proxy-uri care scriu `X-Forwarded-For` înaintea
aplicației. Garanția „elementele din stânga nu sunt folosite" este condiționată de acest
lucru și de nimic altceva.

Cu un singur proxy real, dar `TRUSTED_PROXY_HOPS=2`, un client care trimite
`X-Forwarded-For: 9.9.9.9` face antetul final să fie `9.9.9.9, <IP real>`, iar poziția a
doua de la dreapta este chiar `9.9.9.9` — valoarea aleasă de atacator. Rezultatul este că
rate limiting-ul devine ocolibil printr-un IP diferit la fiecare cerere, iar aplicația fiind
publică și fără cont, consecința directă este cost Voyage și Anthropic nelimitat.

Regula practică: **în caz de dubiu, scade `N`, nu îl crește.** `N` prea mic înseamnă doar
bucket-uri de rate limit mai grosiere (mai mulți vizitatori grupați pe adresa proxy-ului);
`N` prea mare înseamnă rate limiting inexistent.

### Smoke test obligatoriu după deploy

Cu `TRUSTED_PROXY_HOPS=1` setat în producție, verifică manual că un antet trimis de client
nu schimbă bucket-ul:

1. Trimite o cerere normală către `POST /intreaba`, fără `X-Forwarded-For`, și notează
   comportamentul de rate limit.
2. Trimite aceeași cerere cu antetul `X-Forwarded-For: 9.9.9.9` adăugat manual.
3. Repetă pasul 2 cu `X-Forwarded-For: 9.9.9.8`, apoi cu `9.9.9.7`.

Contoarele de rate limit trebuie să crească în **același** bucket la toți pașii, ca și cum
antetul nu ar exista. Dacă în schimb fiecare valoare falsificată pare să primească un buget
proaspăt de 5 cereri pe minut, `TRUSTED_PROXY_HOPS` este prea mare și trebuie coborât
înainte de a deschide accesul public.

### 3.5 Plafon zilnic global pentru apelurile plătite

| Variabilă | Rol |
| --- | --- |
| `DAILY_PAID_CALL_LIMIT` | Numărul maxim de întrebări pe zi calendaristică **UTC** care pot ajunge la un apel plătit (Voyage embed și/sau Anthropic generate). Întreg strict pozitiv; implicit `200` dacă lipsește. |

Acesta e un întrerupător de siguranță la nivelul întregii aplicații, separat de quota de
10 întrebări/browser și de rate limiting-ul per IP: cele două de mai sus se pot ocoli
(ștergerea cookie-ului, respectiv surse IP multiple), dar contorul zilnic e global și
numără independent de cine face cererea.

**Ce se numără:** o întrebare intră la plafon o singură dată, dacă declanșează **cel puțin
unul** dintre apelurile plătite — embedding-ul Voyage (căutare semantică, când întrebarea nu
conține un articol explicit) sau generarea Anthropic (când există dovadă găsită, exact sau
semantic). O întrebare care se rezolvă complet din lookup-ul exact în baza de date, fără
căutare semantică și fără generare (`not_found`, `ambiguous_article`, `ambiguous_reference`
derivate direct din potrivirea exactă), **nu costă nimic și nu se numără**. O întrebare
semantică ce declanșează atât embedding cât și generare numără o singură dată, nu de două ori.

**Ce se întâmplă la atingerea pragului:** apelurile plătite se opresc înainte de a fi făcute
(Voyage/Anthropic nu sunt niciodată contactate), iar răspunsul este exact același `503`
generic („Serviciul este temporar indisponibil.”) folosit pentru orice altă eroare de
infrastructură — deliberat nedistins de un incident tehnic obișnuit, ca să nu scurgă către
public faptul că e vorba de un plafon de cost, pragul configurat sau mecanismul din spate.
Quota personală (10/browser) **nu** se consumă când cererea eșuează din acest motiv.

**Fusul orar al „zilei calendaristice":** contorul se resetează la miezul nopții **UTC**
(ora 00:00 UTC = 02:00 sau 03:00 ora României, în funcție de ora de vară), nu la miezul
nopții local. Alegerea urmează același model ca ferestrele de rate limit din §3.4, care
sunt și ele calculate strict în UTC — un singur fus orar de referință în toată aplicația,
fără conversii ad-hoc.

**Stocare:** contorul este persistat în tabela `public.paid_call_budget`
(`supabase/migrations/20260903120000_paid_call_daily_budget.sql`), un singur rând pe zi
calendaristică, cu aceeași rezervare atomică „increment condiționat de prag, cu
`RETURNING`" folosită deja pentru quota per-browser. Migrația nu a fost aplicată automat;
se rulează manual, la fel ca migrația controalelor anonime din §3.3.

## 4. Antete de securitate HTTP

Fiecare răspuns (inclusiv erorile și fișierele din `/assets/*`) primește:

| Antet | Valoare | De ce |
| --- | --- | --- |
| `Content-Security-Policy` | `default-src 'none'`, `script-src`/`style-src` cu hash-uri `sha256-` exacte ale blocurilor inline din `static/index.html`, `static/termeni.html` și `static/confidentialitate.html` (plus `'unsafe-hashes'` pentru singurul atribut `style=""` inline), `font-src 'self'`, `connect-src 'self'`, `img-src 'self'`, `base-uri 'none'`, `form-action 'self'`, `frame-ancestors 'none'` | UI-ul are CSS/JS inline și fonturi self-hostate din `/assets`; hash-urile permit exact acel conținut, fără `'unsafe-inline'`. O modificare a blocurilor `<style>`/`<script>` inline din oricare din cele trei pagini cere hash-uri noi în `main.py`, altfel pagina se rupe silențios sub CSP. |
| `X-Frame-Options` | `DENY` | Anti-clickjacking pentru browsere fără suport `frame-ancestors`. |
| `X-Content-Type-Options` | `nosniff` | Împiedică MIME-sniffing. |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Nu trimite path/query complet către alte origini. |
| `Permissions-Policy` | dezactivează camera, microfonul, geolocația, plata, USB, senzorii de mișcare și fullscreen | Aplicația nu folosește niciuna dintre ele. |
| `Strict-Transport-Security` | `max-age=15552000` (180 de zile, fără `preload`) | Railway redirecționează deja 301 către HTTPS; antetul e ignorat de browser pe conexiuni HTTP, deci e sigur să fie mereu prezent. Fără `preload` deliberat: înscrierea în lista de preload a browserelor e greu reversibilă. |

## 5. Rute publice

| Rută | Rol |
| --- | --- |
| `GET /` | Aplicația web; emite cookie-ul anonim dacă lipsește sau este invalid. |
| `GET /health` | Healthcheck-ul platformei. |
| `GET /termeni` | Pagina juridică Termeni și condiții; fișier lipsă înseamnă `503` generic. |
| `GET /confidentialitate` | Politica de confidențialitate; fișier lipsă înseamnă `503` generic. |
| `GET /assets/*` | Fișiere statice read-only servite strict din `static/assets/` (fonturi self-hostate, favicon). |
| `GET /documents` | Catalogul public al documentelor `approved` — doar `cod_oficial`, `titlu_oficial`, `an`. Fără cookie/quota/rate limit, la fel ca `/termeni`. |
| `POST /intreaba` | Endpoint-ul de întrebare; aplică quota anonimă și rate limiting. |

Directorul `static/` **nu** este montat integral; nu există niciun endpoint care poate servi
alte fișiere din repo, iar `/assets/*` refuză traversarea de cale.

## 5.1 Curățarea periodică a bucket-urilor de rate limit expirate

`cleanup_rate_limit_buckets.py` șterge fizic rândurile din `public.rate_limit_buckets` cu
`expires_at` în trecut. Logica de ștergere (`PostgresAccessControlRepository.
cleanup_expired_rate_limit_buckets`) exista deja și era testată; scriptul e piesa care
lipsea — nu face parte din procesul web (`Procfile`), trebuie rulat periodic separat:

```powershell
python cleanup_rate_limit_buckets.py --dry-run   # numără, fără DELETE
python cleanup_rate_limit_buckets.py             # șterge și face commit
```

**Cum se programează pe Railway** (nefăcut încă — necesită aprobare separată, e o
schimbare de infrastructură, nu doar cod):

1. În proiectul Railway, adaugă un serviciu nou din același repo (`New Service` →
   `GitHub Repo`, același repo ca `normativai`).
2. Setează comanda de pornire a serviciului nou la `python cleanup_rate_limit_buckets.py`
   (înlocuiește comanda din `Procfile`, care se aplică doar serviciului web).
3. În Settings → **Cron Schedule**, setează o expresie cron (ex. `0 * * * *` — o dată pe
   oră; retenția e de 24h, deci frecvența nu e critică).
4. Copiază exact aceleași variabile `DB_HOST`/`DB_NAME`/`DB_USER`/`DB_PASSWORD`/`DB_PORT`
   de la serviciul `normativai` — serviciul de cleanup nu are nevoie de `VOYAGE_API_KEY`,
   `ANTHROPIC_API_KEY` sau de variabilele `ANONYMOUS_*`.

## 6. Ce NU se pune în variabile de mediu

- Nicio cheie sau parolă nu se comite în repo și nu apare în `DEPLOYMENT.md`, `README.md`
  sau în loguri.
- Scripturile de ingestion (`populare_db.py`, `procesare_documente.py`) nu fac parte din
  procesul web și nu trebuie rulate automat la deploy; importul de documente rămâne o
  operație manuală, decisă explicit.

## 7. Restanțe cunoscute înainte de lansare publică

- Ștergerea fizică a bucket-urilor IP expirate (24 de ore): logica există și e testată
  (`cleanup_rate_limit_buckets.py`, §5.1), dar programarea periodică pe Railway (Cron
  Schedule) nu a fost creată încă — rulează doar manual până atunci. Același lucru e
  valabil, la o scară mult mai mică, pentru rândurile din `public.paid_call_budget` (unul
  pe zi calendaristică) — nicio ștergere programată acolo, dar volumul e neglijabil.
- Afirmațiile din paginile juridice (regiunea Supabase, infrastructura de hosting, adresa de
  contact) trebuie verificate periodic dacă infrastructura se schimbă.
- Review de securitate independent final — nu a fost efectuat încă înainte de expunerea
  publică completă (dincolo de cei 4 testeri controlați).
