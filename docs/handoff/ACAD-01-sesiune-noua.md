# ACAD-01 — Brief pentru sesiunea separată: add-on Omnia pentru AutoCAD

Data: 27-09-2026. De la: Planner-ul sesiunii Omnia (R14–R16). Pentru: o sesiune nouă, separată (Claude Code sau Pi), care lucrează **în paralel** cu munca de pe RAG.

## Citește întâi
1. `docs/autocad/INTENT.md` (în repo-ul `D:\Omnia-MVP`, branch `main` după merge) — problema, v1, constrângeri, întrebări deschise.
2. `AGENTS.md` și `~/.agents/GLOBAL.md` — regulile globale (în special: **nimic instalat sau lucrat pe C:**, fără secrete, flux de 4 agenți, predare prin fișiere).

## Sarcina ta, în ordine
1. **Inventar de mediu (read-only):** versiunea exactă de AutoCAD instalată și calea ei; dacă există .NET 8 SDK și WebView2 Runtime; ce lipsește. Nu instala nimic fără aprobarea lui Lucian, și nimic pe C:.
2. **Clarifică cu Lucian** întrebările deschise din `INTENT.md` (măcar 1–3) și notează răspunsurile în `INTENT.md`.
3. **Scrie `docs/autocad/SPEC.md`** (cerințe + design v1 + conflicte cu reguli existente) și cere aprobarea lui Lucian.
4. Abia după aprobare: proiect nou în `D:\Omnia-AutoCAD` (repo git separat), prototip v1, flux de 4 agenți pentru cod.

## Constrângeri dure
- **Nu modifica** nimic din `D:\Omnia-MVP` în afară de `docs/autocad/` și `docs/handoff/ACAD-*` (pe branch propriu, prin PR). Munca pe RAG (R16+) continuă în paralel acolo, într-o altă sesiune.
- Nu apela `/intreaba` în bucle sau teste automate: fiecare apel costă (Voyage + Anthropic) și consumă cota anonimă. Testele reale cer aprobarea lui Lucian.
- Nu folosi și nu copia `.env`-ul Omnia; add-on-ul v1 nu are nevoie de chei.
- Statusul se raportează în `docs/handoff/ACAD-<nr>-*-raport.md`, nu doar în conversație.

## Rezultat așteptat al primei runde
`docs/handoff/ACAD-01-raport.md`: inventarul de mediu, răspunsurile lui Lucian, link la `SPEC.md` propus și ce aprobare urmează.
