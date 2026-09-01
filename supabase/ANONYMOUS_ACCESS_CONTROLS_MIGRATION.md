# Draft migrare — controale anonime

Fișierul `20260831230000_anonymous_access_controls.sql` este doar draft versionat; nu a fost aplicat în Supabase.

## Ce creează

- `anonymous_usage`: numai `visitor_hash` HMAC și contorul 0–10; nu conține ID-ul cookie sau cookie-ul.
- `rate_limit_buckets`: numai `ip_hash` HMAC, bucket-uri `minute`/`hour` și expirare fixă la 24 de ore; nu conține IP brut.
- index pentru cleanup după `expires_at`, RLS activ fără politici și `REVOKE ALL` pentru `anon`/`authenticated`.

## Preflight și aplicare ulterioară

Migrarea eșuează înainte de DDL dacă oricare tabel există deja sau rolurile Supabase necesare lipsesc. Rulează într-o singură tranzacție; orice eroare face rollback automat. Aplicarea persistentă cere aprobarea explicită a lui Lucian și nu face parte din Faza 4A.

## Gate SQL tranzacțional executat

Gate-ul aprobat a fost executat pentru migrarea cu prefix SHA-256 `a2840a5364f0`, în interiorul unei tranzacții încheiate cu `ROLLBACK`; aplicarea persistentă **nu** a fost făcută.

În tranzacție s-au verificat factual: 2 tabele create, coloanele așteptate, 10 constraints, RLS `true` pe ambele tabele, zero politici, zero granturi pentru `anon`/`authenticated`, indexul de cleanup prezent și zero rânduri noi.

Snapshot-ul existent a rămas: 2 documente, 694 chunk-uri și 2 documente `approved`. După `ROLLBACK`, o conexiune read-only nouă a confirmat că ambele tabele sunt absente și snapshot-ul este neschimbat.

Concurența cross-session nu a fost testată: DDL-ul necomis nu este vizibil altor sesiuni. Această verificare rămâne obligatorie după aplicarea persistentă aprobată.

## Contract runtime pentru integrarea viitoare

Acest contract este documentat, dar **nu este integrat în `main.py`/FastAPI** în Faza 4A.

1. După validarea inputului, rate limit-ul rulează primul, înainte de Voyage/Claude, într-o tranzacție dedicată. Callerul face `commit` atât pentru `allowed=True`, cât și pentru `allowed=False`: fiecare tentativă validă crește atomic bucket-urile minut și oră, iar decizia se ia după incrementare. O cerere blocată nu rezervă quota anonimă.
2. Numai după un rate limit permis, quota se rezervă în tranzacția cererii. Callerul face `commit` pentru statusurile `answered`, `not_found`, `ambiguous_article` și `ambiguous_reference`.
3. Pentru HTTP 503 sau erori DB/Voyage/Claude, callerul face `rollback` al tranzacției quota, deci rezervarea nu se consumă. Inputul invalid este respins înainte de ambele tranzacții.
4. Cleanup-ul șterge bucket-urile cu `expires_at` atins; retenția IP este fixă la maximum 24 de ore. Cleanup-ul are propriul commit explicit ales de caller.

## Rollback structural

După aprobare și numai dacă trebuie eliminat draftul deja aplicat, se rulează separat:

```sql
begin;
drop table public.rate_limit_buckets;
drop table public.anonymous_usage;
commit;
```

Nu se acordă granturi publice la rollback. Orice schimbare ulterioară de politici sau granturi necesită o decizie separată.
