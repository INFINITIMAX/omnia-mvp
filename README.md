# Omnia — rulare locală minimă

## Pregătire

Este necesar Python 3.11+ și un mediu virtual activat.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Teste locale, fără servicii externe

```powershell
python -m pytest -q
```

Testele folosesc clienți falși (mock-uri). Ele nu citesc `.env` și nu apelează Anthropic, Voyage sau Supabase.

## Verificarea ingestion-ului fără cost

Dacă există documente locale pregătite în `documente_noi/`, rulează:

```powershell
python populare_db.py --dry-run
```

Comanda validează metadata și chunking-ul, dar nu creează embeddings și nu modifică Supabase.

## Pornire API (opțională)

API-ul necesită variabilele de mediu configurate local; nu introduce secrete în Git.

```powershell
python -m uvicorn main:app --reload
```
