# Gate-uri — refuz calcule/proiectare

## Rezultate observabile

1. `POST /intreaba` detectează local, determinist și conservator cererile de execuție a unui calcul, estimări sau dimensionări și răspunde HTTP 200 cu statusul, mesajul și citările aprobate.
2. Pentru acest refuz, rate limit-ul rămâne contabilizat, quota este restituită verificat fail-closed, iar catalogul, retrieval-ul, Voyage și Anthropic nu sunt apelate.
3. Întrebările despre metodă, formule, praguri, valori prescrise, debit minim și localizarea explicației într-un articol nu sunt clasificate drept execuție de calcul; excepțiile nu pot ocoli un imperativ explicit.
4. Matricea include cererile mixte (metodă + imperativ), puterea în kW, capacitatea frigorifică și capacitatea de răcire instalată, toate refuzate local.
5. UI-ul afișează răspunsul normal, îl păstrează în istoricul vizibil și nu îl trimite în `context_conversatie` ulterior.
6. Promptul interzice categoric executarea calculelor, estimărilor și dimensionărilor; CSP-ul permite scriptul inline actualizat.

## Comenzi pentru Planner (PowerShell; nu sunt executate de Coder)

```powershell
Set-Location D:\Omnia-MVP-no-calculations
python -m pytest -q
python -m pytest -q tests\test_api_integration.py tests\test_generation_core.py tests\test_ui_static.py
python -c "from pathlib import Path; import base64, hashlib, re; text=Path('static/index.html').read_text(encoding='utf-8'); script=re.search(r'<script>(.*)</script>', text, re.S).group(1).encode(); print(base64.b64encode(hashlib.sha256(script).digest()).decode())"
git diff --check
git status --short
git diff --cached --name-only
```
