# Draft migrare — controale anonime

Fișierul `20260831230000_anonymous_access_controls.sql` este doar draft versionat; nu a fost aplicat în Supabase.

## Ce creează

- `anonymous_usage`: numai `visitor_hash` HMAC și contorul 0–10; nu conține ID-ul cookie sau cookie-ul.
- `rate_limit_buckets`: numai `ip_hash` HMAC, bucket-uri `minute`/`hour` și expirare fixă la 24 de ore; nu conține IP brut.
- index pentru cleanup după `expires_at`, RLS activ fără politici și `REVOKE ALL` pentru `anon`/`authenticated`.

## Preflight și aplicare ulterioară

Migrarea eșuează înainte de DDL dacă oricare tabel există deja sau rolurile Supabase necesare lipsesc. Rulează într-o singură tranzacție; orice eroare face rollback automat. Aplicarea persistentă cere aprobarea explicită a lui Lucian și nu face parte din Faza 4A.

## Rollback structural

După aprobare și numai dacă trebuie eliminat draftul deja aplicat, se rulează separat:

```sql
begin;
drop table public.rate_limit_buckets;
drop table public.anonymous_usage;
commit;
```

Nu se acordă granturi publice la rollback. Orice schimbare ulterioară de politici sau granturi necesită o decizie separată.
