# Migrare aplicată — controale anonime

Artefactul exact executat înaintea corecției comment-only avea prefix SHA-256 `a2840a5364f0` și a fost aplicat persistent la 01-09-2026 (România), printr-o tranzacție PostgreSQL directă. Fișierul curent diferă doar prin comentariul de stare de la început; statement-urile SQL executabile sunt neschimbate. Nu se afirmă înregistrarea în istoricul migrărilor.

## Ce creează

- `anonymous_usage`: numai `visitor_hash` HMAC și contorul 0–10; nu conține ID-ul cookie sau cookie-ul.
- `rate_limit_buckets`: numai `ip_hash` HMAC, bucket-uri `minute`/`hour` și expirare fixă la 24 de ore; nu conține IP brut.
- index pentru cleanup după `expires_at`, RLS activ fără politici și `REVOKE ALL` pentru `anon`/`authenticated`.

## Preflight și aplicare

Migrarea eșuează înainte de DDL dacă oricare tabel există deja sau rolurile Supabase necesare lipsesc. A rulat într-o singură tranzacție PostgreSQL directă; orice eroare ar fi făcut rollback automat.

## Validare persistentă

O conexiune nouă a confirmat `PASS` după aplicare: 2 tabele, coloanele așteptate, 10 constraints, RLS `true` pe ambele tabele, zero politici, zero granturi pentru `anon`/`authenticated`, indexul de cleanup și inițial zero rânduri.

Snapshot-ul existent a rămas intact: 2 documente, 694 chunk-uri și 2 documente `approved`. Tabela internă `supabase_migrations.schema_migrations` nu a fost vizibilă conexiunii; nu se afirmă înregistrarea în istoricul migrărilor și acesta nu a fost modificat manual.

Gate-ul de concurență real a folosit hash-uri sintetice: quota pornită la 9, două conexiuni au returnat `[false, true]`, iar valoarea finală a fost 10. Rate limit-ul pornit la 4, două conexiuni au returnat `[false, true]`, iar contoarele au ajuns la 6; a treia cerere blocată le-a crescut la 7. Cleanup-ul sintetic a fost verificat, iar ambele tabele au avut la final zero rânduri.

## Contract runtime pentru integrarea viitoare

Acest contract este documentat, dar **nu este integrat în `main.py`/FastAPI** în Faza 4A.

1. După validarea inputului, rate limit-ul rulează primul, înainte de Voyage/Claude, într-o tranzacție dedicată. Callerul face `commit` atât pentru `allowed=True`, cât și pentru `allowed=False`: fiecare tentativă validă crește atomic bucket-urile minut și oră, iar decizia se ia după incrementare. O cerere blocată nu rezervă quota anonimă.
2. Numai după un rate limit permis, quota se rezervă în tranzacția cererii. Callerul face `commit` pentru statusurile `answered`, `not_found`, `ambiguous_article` și `ambiguous_reference`.
3. Pentru HTTP 503 sau erori DB/Voyage/Claude, callerul face `rollback` al tranzacției quota, deci rezervarea nu se consumă. Inputul invalid este respins înainte de ambele tranzacții.
4. Cleanup-ul șterge bucket-urile cu `expires_at` atins; retenția IP este fixă la maximum 24 de ore. Cleanup-ul are propriul commit explicit ales de caller.

## Rollback structural

Dacă trebuie eliminată schema deja aplicată, se rulează separat, numai cu aprobare:

```sql
begin;
drop table public.rate_limit_buckets;
drop table public.anonymous_usage;
commit;
```

Nu se acordă granturi publice la rollback. Orice schimbare ulterioară de politici sau granturi necesită o decizie separată.
