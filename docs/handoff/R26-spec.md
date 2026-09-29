# R26 — Spec: P 118/2-2013 și P 118/3-2015 consolidate (D27)

Status: draft planner, 29-09-2026 (lucru autonom aprobat de Lucian; fără DB/Voyage/merge/deploy).

## Intent
Aplicația răspunde și din P 118/2 (instalații de stingere) și P 118/3 (detectare/alarmare), în varianta
**în vigoare** (Ordinele 6026/2018 și 6025/2018 aplicate), cu proveniența vizibilă pentru orice text
modificat. Nimic redactat de noi: fiecare fragment e verificabil literal în MO de bază sau în ordin.

## Surse
| Document | Bază | Modificări |
|---|---|---|
| P 118/2-2013 | `P118-2 final.pdf` (glife Ń→ț, ł→Ț, ǎ→ă, ş/Ş sedilă) — varianta pre-publicare a ordinului („ORDINUL nr…din…2013”); de confirmat identitatea de conținut cu cealaltă sursă | Ordin 6026/2018, MO 966/15-11-2018 |
| P 118/3-2015 | MO 243 bis/09-04-2015 (`p118_3/migs_P118_3.pdf`), diacritice (cid:N) → tabelă per font | Ordin 6025/2018, MO 977/19-11-2018 (Portal Legislativ) |

## Design
1. **Text de bază curat**: P 118/2 — mapare glife în `diacritice.py` (ca R22), doar caractere dovedite,
   absente din celelalte 9 documente. P 118/3 — extragere pdfplumber + tabelă CID per font (dată de planner).
2. **Consolidare** — modul nou `consolidare_normative.py`, fără rețea/DB:
   - operații JSON scrise de coder citind ordinul: înlocuire punct; înlocuire subunitate (alineat/literă/
     parte introductivă, imbricat); inserare după subunitate; abrogare punct/subunitate; renumerotare+
     înlocuire; înlocuire bloc între ancore (tabele, anexe); înlocuire globală de sintagmă;
   - verificări fail-closed: `text_nou` apare literal în ordin (spații normalizate); ținta există exact o
     dată în bază; textul vechi al țintei nu mai există după aplicare; nr. operații == nr. puncte din ordin;
   - proveniență: marcaj fix la finalul fiecărui text modificat/inserat/abrogat, ex.
     `[Text modificat prin Ordinul nr. 6.025/2018, publicat în Monitorul Oficial nr. 977 din 19.11.2018]`.
3. **Runtime** (task separat): câmp `modificat_prin` în citare, derivat server-side din marcaj; UI îl afișează.
   Fără migrare DB. Deploy = aprobare Lucian.
4. **Import**: documente noi `p118_2_2013`, `p118_3_2015`, dry-run fără cost; commit/`approved` = Lucian.
   `p118_2_2013_modificari` rămâne `disabled`.
5. **Set de aur**: +2–3 întrebări per document, verificate în textul consolidat (versiune set = 1).

## Conflicte semnalate
- NTPEE-2009 respins ca „variantă agregată” → D27: consolidare doar cu proveniență vizibilă per fragment
  (aprobat Lucian 28-09-2026).
- Regula „doar MO”: baza P 118/2 nu e tipăritura MO → de raportat lui Lucian.
