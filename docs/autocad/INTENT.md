# Intent: Omnia în AutoCAD (add-on)
Status: draft — 27-09-2026. Aprobat ca direcție de Lucian; spec-ul urmează după clarificarea întrebărilor de mai jos.

## Problema
Proiectanții lucrează în AutoCAD. Ca să verifice o prevedere normativă, ies din desen, deschid browserul, caută, revin. Fluxul se rupe și răspunsul nu ajunge lângă elementul la care se referă.

## Rezultat propus
**v1 (acum):** o paletă andocabilă în AutoCAD 2025+ care afișează interfața existentă `https://normativai.ro`, deschisă cu o comandă (ex. `OMNIA`). Fără logică nouă de RAG: add-on-ul e doar un „cadru” pentru produsul existent, cu toate garanțiile lui (citare verificată, refuz onest, fără calcule de proiectare).

**Mai târziu (proiect mai complex, de detaliat):** context din desen (text/strat selectat → întrebare), inserarea unei citări ca MText/notă în desen, autentificare și cote pentru utilizatori profesioniști, API dedicat.

## Utilizatori/sisteme afectate
- Proiectanți (instalații, arhitectură) care folosesc AutoCAD 2025+ (full, nu LT — LT nu încarcă plugin-uri .NET).
- NormativAI în producție: traficul din AutoCAD trece prin aceeași rută `/intreaba`, cu aceleași cote anonime (10 întrebări/vizitator, 5/min + 30/oră per IP, plafon zilnic global 200 — vezi `access_control.py`, audit R10 F5).
- Repo-ul Omnia **nu** se modifică în v1; add-on-ul e un proiect separat.

## Constrângeri cunoscute
- **Tehnologie v1:** plugin .NET 8 pentru AutoCAD 2025+ (`PaletteSet` + `WebView2`). Referințe AutoCAD prin pachetele NuGet oficiale `AutoCAD.NET` 25.x (a se verifica versiunea exactă față de AutoCAD-ul instalat).
- **Regula globală „nimic pe C:”:** SDK-uri, cod, build-uri, date pe `D:\`. Puncte care o ating și trebuie rezolvate explicit în spec:
  - folderul de date WebView2 (cookie-ul anonim, cache) ar merge implicit în `%LOCALAPPDATA%` (C:) → setat explicit pe `D:\`;
  - autoloader-ul AutoCAD (`ApplicationPlugins`) e în `C:\ProgramData\Autodesk\…` → alternativă: încărcare din `D:\` (NETLOAD / demand-load din registru) sau excepție aprobată explicit.
- **Securitate:** fără chei sau secrete în add-on; WebView2 navighează doar pe `normativai.ro` (restul linkurilor în browserul extern). CSP/X-Frame-Options ale site-ului nu blochează WebView2 ca pagină de nivel superior (nu e iframe) — de confirmat în prototip.
- **Lucru în paralel:** sesiune separată, worktree/repo separat pe `D:\`; comunicarea cu această sesiune doar prin fișiere (`docs/handoff/`). Excepție explicită de la regula de lucru secvențial din `AGENTS.md` (regula 4), aprobată de Lucian 27-09-2026 **doar** pentru add-on-ul AutoCAD, care nu atinge codul Omnia.

## Întrebări deschise (de clarificat înainte de spec)
1. Distribuție: doar pe mașina lui Lucian (v1), pentru colegi, sau public (Autodesk App Store — cerințe de semnare/certificare)?
2. Cotele anonime ajung pentru uz real în AutoCAD, sau v1 trebuie deja să prevadă autentificare/cotă dedicată?
3. Unde se instalează și se încarcă plugin-ul, ținând cont de regula „nimic pe C:” (vezi mai sus)?
4. Ce versiuni/vertical-uri exacte de AutoCAD (AutoCAD, AutoCAD MEP, Architecture) trebuie suportate?
5. Pentru „mai târziu”: ce contexte din desen contează cel mai mult (text selectat, blocuri, straturi, atribute)?
6. Semnarea codului (certificat) — necesară pentru a evita avertismentele de securitate AutoCAD la încărcare?

## Criterii de „gata” pentru v1 (propuse)
- Comanda `OMNIA` deschide/închide paleta în AutoCAD 2025+; paleta rămâne andocabilă și își păstrează poziția.
- Întrebare → răspuns cu citări, identic cu site-ul; cookie-ul anonim persistă între sesiuni AutoCAD.
- Zero fișiere de lucru pe C: în afara celor impuse de AutoCAD și aprobate explicit.
- Instrucțiuni de instalare/dezinstalare de un paragraf.
