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
  pentru că numai acele poziții sunt scrise de infrastructura proprie. Elementele din
  stânga sunt controlate de client și nu sunt niciodată folosite.
- Dacă antetul lipsește, are mai puține elemente decât `N`, sau elementul selectat nu este
  o adresă IP literală validă, se cade înapoi pe `request.client.host`. Nu se acceptă
  niciodată o valoare neverificată.
- O valoare care nu este un întreg nenegativ produce `503` generic la pornirea cererii,
  la fel ca orice altă configurație invalidă.

**Valoarea pentru Railway:** `TRUSTED_PROXY_HOPS=1`.

Fără această setare, în spatele proxy-ului Railway toți vizitatorii ar împărți un singur
bucket de rate limit (5 cereri/minut și 30/oră **în total**, pentru toată lumea), pentru că
`request.client.host` ar fi adresa proxy-ului, nu a vizitatorului.

## 4. Rute publice

| Rută | Rol |
| --- | --- |
| `GET /` | Aplicația web; emite cookie-ul anonim dacă lipsește sau este invalid. |
| `GET /health` | Healthcheck-ul platformei. |
| `GET /termeni` | Pagina juridică Termeni și condiții. |
| `GET /confidentialitate` | Politica de confidențialitate. |
| `GET /assets/*` | Fișiere statice read-only servite strict din `static/assets/` (fonturi self-hostate, favicon). |
| `POST /intreaba` | Endpoint-ul de întrebare; aplică quota anonimă și rate limiting. |

Directorul `static/` **nu** este montat integral; nu există niciun endpoint care poate servi
alte fișiere din repo, iar `/assets/*` refuză traversarea de cale.

## 5. Ce NU se pune în variabile de mediu

- Nicio cheie sau parolă nu se comite în repo și nu apare în `DEPLOYMENT.md`, `README.md`
  sau în loguri.
- Scripturile de ingestion (`populare_db.py`, `procesare_documente.py`) nu fac parte din
  procesul web și nu trebuie rulate automat la deploy; importul de documente rămâne o
  operație manuală, decisă explicit.

## 6. Restanțe cunoscute înainte de lansare publică

- Ștergerea fizică a bucket-urilor IP expirate (24 de ore) nu are încă scheduler; expirarea
  este doar logică.
- `GET /documents` nu există; UI-ul nu trebuie să afișeze contoare de documente.
- Afirmațiile din paginile juridice (regiunea Supabase, infrastructura de hosting, adresa de
  contact) trebuie verificate înainte de publicare.
