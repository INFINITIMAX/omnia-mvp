# Maparea glifelor CambriaMath (fara ToUnicode)

Mapare GID -> caracter real pentru fontul incorporat "CambriaMath" (subset CIDFontType0, Identity-H) gasit in PDF-urile din documente_noi. Codul CID din fluxul PDF este chiar GID-ul din fontul original Windows "Cambria Math" (verificat: CID 1848 -> U+1D449 MATHEMATICAL ITALIC CAPITAL V, exact litera 'V' din formula de debit V-punct a art. 14.6). Nu exista dictionar /ToUnicode incorporat, asa ca extragerea implicita PyMuPDF fabrica code point-uri fara legatura cu sensul real (silabe etiopiene, litere siriace, cifre tamile, semne malayalam etc.) pentru orice GID fara intrare cmap directa.

## Cauza

documente_noi/i9_2022/source.pdf (si, marginal, p118_1_2025) contin formule culese cu fontul `CambriaMath`, incorporat ca subset `CIDFontType0` cu codificare `Identity-H` si **fara dictionar `/ToUnicode`**. PyMuPDF (`page.get_text()`) foloseste un euristic intern cand nu gaseste un ToUnicode valid si produce code point-uri fara nicio legatura cu sensul real (silabe etiopiene, litere siriace, cifre tamile, semne malayalam).

## Metoda de reconstructie

Pentru fiecare GID folosit efectiv in PDF-urile din documente_noi (colectat prin page.get_texttrace(), care expune GID-ul real per caracter, spre deosebire de euristicul stricat al get_text()): (1) incercam rezolvarea prin cmap-ul propriu al fontului de referinta (GID -> nume glif -> Unicode) - acopera glifele pe care Word/generatorul PDF le poate adresa direct prin codpoint (litere, cifre, greceste, operatori matematici, alfanumerice italice matematice); (2) pentru rest (variante optice mici folosite la indici/exponenti si piese de constructie pentru paranteze/radicali mari, care exista doar ca glife fara nicio asignare Unicode - normal pentru fonturi matematice OpenType), randam conturul glifului direct din GID cu FreeType si il identificam vizual, verificat incrucisat cu contextul semantic al glifelor vecine deja rezolvate din aceeasi formula. GID-urile care nu au putut fi identificate cu incredere sunt inregistrate cu method='unresolved' si char=null; codul de extragere nu trebuie sa ghiceasca niciodata pentru acestea.

Fontul de referinta este `C:/Windows/Fonts/cambria.ttc`, fata (face) index 1, numita intern "Cambria Math" — versiunea completa, nesubsetata, a fontului folosit la compunerea PDF-ului.

**Ancora de verificare**: CID 1848 (glif folosit efectiv in art. 14.6) se rezolva la U+1D449 MATHEMATICAL ITALIC CAPITAL V, exact litera 'V' din formula de debit V-punct. Formula completa a art. 14.6 a fost reconstruita si verificata folosind aceasta tabela (vezi raportul din task).

## Format

Fisierul `cambria_math_glyph_map.json` are cheia `entries`, un dictionar `"<gid>": {char, unicode, method, glyph_name, note}` unde:
- `char` — caracterul real (asa cum trebuie sa apara in text)
- `method` — `cmap` (rezolvat automat, cu incredere maxima, din tabela cmap a fontului de referinta) sau `visual` (identificat prin randare directa a glifului cu FreeType si citire vizuala, pentru glife fara intrare cmap — de obicei variante optice mici folosite de Word pentru indici/exponenti, sau piese de constructie pentru paranteze/radicali mari)
- `note` — justificarea/verificarea specifica acelei intrari

Nicio intrare nu are `char: null` in acest fisier — toate cele 174 de glife folosite efectiv in cele doua documente au fost identificate. Daca un document viitor foloseste un GID nou, absent din tabela, codul de extragere **nu trebuie sa ghiceasca** — trebuie sa marcheze explicit locul (vezi `glyph_mapping.py`, functia `_gid_la_caracter`, care produce un marcaj de forma `<?glifNNNN?>`).

## Normalizare stilistica la incarcare (nu in acest fisier)

`char` din acest JSON e **identitatea bruta a glifului** (verificabila direct
impotriva fontului de referinta) — pastram intentionat aici, de ex., `𝑽`
(U+1D449 MATHEMATICAL ITALIC CAPITAL V), nu `V`, ca sa ramana o inregistrare
fidela a ce e gliful, nu a cum vrem sa apara in text.

Normalizarea stilistica (bold/italic -> litera simpla) se aplica separat, la
`glyph_mapping.incarca_tabela()`, pentru orice caracter din blocul Unicode
"Mathematical Alphanumeric Symbols" (U+1D400-U+1D7FF): fontul Cambria Math
foloseste acele code point-uri pentru variantele stilizate (italic, bold,
bold-italic, script, fraktur, double-struck, sans-serif, monospace) ale
literelor si cifrelor, in loc sa aplice stilul vizual peste litera obisnuita.
Nu e continut matematic, e doar stilizare — lasate asa, aceste caractere:
- nu sunt acoperite de fonturile aplicatiei (subset latin/latin-ext) -> patrate goale in UI
- nu se potrivesc la o cautare exacta dupa litera simpla ('V' != '𝑽')
- se tokenizeaza prost la embeddings (caractere foarte rare)

Verificat (nu presupus): toate cele 996 de code point-uri asignate in bloc se
descompun curat, prin `unicodedata.normalize('NFKC', ...)`, la EXACT un singur
caracter simplu in afara blocului — inclusiv toate cifrele stilizate si toate
variantele de stil enumerate mai sus. Simbolurile matematice reale (radical
√, inmultire ×, ≤, ≥, punctul suprapus combinat U+0307, literele grecesti
simple ca α/λ/π/ρ/Σ/θ care NU sunt in acest bloc) raman neatinse: nu au
descompunere de compatibilitate, deci `normalize()` nu le modifica.

**Limita cunoscuta, in afara scopului acestei normalizari**: caracterele din
blocul "Letterlike Symbols" (U+2100-214F) — ex. U+210E PLANCK CONSTANT,
folosit in document ca litera italica "h" generica (nu ca simbol Planck) —
nu sunt in blocul Mathematical Alphanumeric Symbols si NU sunt normalizate
automat, desi au acelasi risc teoretic de acoperire font. Apar de 4 ori in
i9_2022 (formula art. 12.1, variabila "h" din pierderea de sarcina locala).
Nefiind cerute explicit in normalizare, au fost doar raportate, nu corectate.

## Limitari cunoscute

Corectia efectiva a textului (nu identificarea glifelor - toate cele 174 sunt identificate cu certitudine) se face in `glyph_mapping.py`, care asociaza span-urile din `page.get_texttrace()` (GID adevarat) cu span-urile din `page.get_text("dict")` (segmentarea proprie a PyMuPDF, ce va deveni literal `page.get_text()`), prin distanta de la centrul span-ului dict la bbox-ul candidatului.

**Proxy de glife invatat pe document** (`invata_proxy_glife`): am verificat ca `page.get_text("dict")` elimina sistematic anumite glife cu latime zero din propria segmentare — pe o pagina cu 8 aparitii ale literei "V" (gid 1848) din notatia V-punct, dict raporteaza span propriu pentru UNA singura, desi `page.get_text()` simplu le contine pe toate ca text (nu e o eroare de-a noastra de potrivire, e o inconsistenta intre cele doua cai de extragere ale PyMuPDF). Fallback-ul stricat al PyMuPDF e insa determinist per GID (verificat pe zeci de aparitii: gid 1848 produce mereu U+0738, gid 4662 mereu U+1236). Scanam tot documentul o data si invatam, per GID, ce caracter stricat produce dict pentru el, DOAR din potriviri de incredere (un singur span dict contiguu, cu lungime exacta egala cu numarul de GID-uri ale candidatului — am verificat empiric ca la potriviri asamblate din MAI MULTE span-uri dict concatenate, chiar daca lungimea totala coincide, corespondenta pozitie-cu-pozitie poate fi decalata, deci nu invatam de acolo). Daca acelasi GID pare sa produca caractere diferite in doua locuri (contrazice determinismul), il scoatem din proxy — nu ghicim intre variante. Acest proxy e folosit ca rezerva DOAR cand `page.get_text("dict")` nu da niciun caracter pentru un candidat (span omis complet), si DOAR daca avem proxy pentru fiecare GID al candidatului respectiv; cand dict chiar da ceva, il folosim asa cum e (mai precis, legat de pozitia reala).

Cu acest mecanism, aparitiile ramase nereparate din i9_2022 au scazut la aproximativ 317 caractere din cele 3093 CambriaMath (~10%; alte ~30 de caractere "suspecte" raportate initial erau typo-uri preexistente in alte fonturi — ex. "centralǎ" in loc de "centrală", in TimesNewRomanPSMT — nelegate de aceasta problema, deci in afara scopului). Ce ramane:

- **Formule cu fractie stivuita 2D real** (ex. art. 11.13, "[l/s]" randat ca fractie verticala l peste s, nu ca text inline "l/s"): `page.get_text("dict")` pune bucatile pe "linii" diferite in ordine care nu respecta citirea naturala (secventa reala e "l", NOU RAND, "s", NOU RAND, "/", nu "l/s" simplu), asa ca needle-ul asamblat din stanga-la-dreapta dupa x0 nu se mai potriveste cu textul real. Corectarea glifelor individuale ramane corecta, doar coada acestei formule (unitatea si numarul ecuatiei) ramane needit.
- **Cazuri foarte rare unde nici dict, nici proxy-ul nu acopera un GID**: cateva aparitii (verificate: 3 pentru gid 1848 in tot documentul, coborat de la 80) raman needite - fie contextul lor local nu ofera nicio potrivire de incredere de la care sa invete proxy-ul, fie GID-ul lor propriu nu apare niciodata izolat, intr-un span dict contiguu, nicaieri in document.
- **Extinderea radicalului (√)** nu e delimitata automat in text (nu inseram paranteze in jurul radicandului) — riscul de a delimita gresit intinderea reala a semnului radical intr-o formula generica a fost considerat mai mare decat beneficiul.

## Tabelul complet (174 intrari)

| GID | Caracter | Unicode | Metoda | Nume glif (font referinta) | Nota |
|---|---|---|---|---|---|
| 3 | ` ` | U+0020 | cmap | `space` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 14 | `K` | U+004B | cmap | `K` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 26 | `W` | U+0057 | cmap | `W` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 133 | `c` | U+0063 | cmap | `c` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 139 | `i` | U+0069 | cmap | `i` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 142 | `l` | U+006C | cmap | `l` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 143 | `m` | U+006D | cmap | `m` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 145 | `o` | U+006F | cmap | `o` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 149 | `s` | U+0073 | cmap | `s` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 163 | `ă` | U+0103 | cmap | `abreve` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 232 | `ș` | U+0219 | cmap | `uni0219` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 236 | `ț` | U+021B | cmap | `uni021B` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 481 | `,` | U+002C | cmap | `comma` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 482 | `;` | U+003B | cmap | `semicolon` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 484 | `.` | U+002E | cmap | `period` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 512 | `/` | U+002F | cmap | `slash` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 581 | `θ` | U+03B8 | cmap | `theta` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 882 | `0` | U+0030 | cmap | `zero` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 883 | `1` | U+0031 | cmap | `one` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 884 | `2` | U+0032 | cmap | `two` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 885 | `3` | U+0033 | cmap | `three` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 886 | `4` | U+0034 | cmap | `four` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 887 | `5` | U+0035 | cmap | `five` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 888 | `6` | U+0036 | cmap | `six` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 889 | `7` | U+0037 | cmap | `seven` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 890 | `8` | U+0038 | cmap | `eight` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 891 | `9` | U+0039 | cmap | `nine` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 892 | `⁰` | U+2070 | cmap | `uni2070` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 932 | `⁄` | U+2044 | cmap | `fraction` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 942 | `∙` | U+2219 | cmap | `uni2219` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 958 | `√` | U+221A | cmap | `radical` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 959 | `∆` | U+2206 | cmap | `Delta` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 963 | `∑` | U+2211 | cmap | `summation` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 1668 | `⋅` | U+22C5 | cmap | `dotmath` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 1827 | `𝐴` | U+1D434 | cmap | `u1D434` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 1828 | `𝐵` | U+1D435 | cmap | `u1D435` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 1829 | `𝐶` | U+1D436 | cmap | `u1D436` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 1830 | `𝐷` | U+1D437 | cmap | `u1D437` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 1831 | `𝐸` | U+1D438 | cmap | `u1D438` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 1834 | `𝐻` | U+1D43B | cmap | `u1D43B` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 1837 | `𝐾` | U+1D43E | cmap | `u1D43E` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 1838 | `𝐿` | U+1D43F | cmap | `u1D43F` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 1840 | `𝑁` | U+1D441 | cmap | `u1D441` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 1843 | `𝑄` | U+1D444 | cmap | `u1D444` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 1845 | `𝑆` | U+1D446 | cmap | `u1D446` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 1847 | `𝑈` | U+1D448 | cmap | `u1D448` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 1848 | `𝑉` | U+1D449 | cmap | `u1D449` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 1849 | `𝑊` | U+1D44A | cmap | `u1D44A` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 1853 | `𝑎` | U+1D44E | cmap | `u1D44E` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 1854 | `𝑏` | U+1D44F | cmap | `u1D44F` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 1855 | `𝑐` | U+1D450 | cmap | `u1D450` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 1856 | `𝑑` | U+1D451 | cmap | `u1D451` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 1857 | `𝑒` | U+1D452 | cmap | `u1D452` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 1858 | `𝑓` | U+1D453 | cmap | `u1D453` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 1859 | `𝑔` | U+1D454 | cmap | `u1D454` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 1860 | `ℎ` | U+210E | cmap | `uni210E` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 1861 | `𝑖` | U+1D456 | cmap | `u1D456` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 1863 | `𝑘` | U+1D458 | cmap | `u1D458` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 1864 | `𝑙` | U+1D459 | cmap | `u1D459` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 1865 | `𝑚` | U+1D45A | cmap | `u1D45A` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 1866 | `𝑛` | U+1D45B | cmap | `u1D45B` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 1867 | `𝑜` | U+1D45C | cmap | `u1D45C` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 1868 | `𝑝` | U+1D45D | cmap | `u1D45D` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 1870 | `𝑟` | U+1D45F | cmap | `u1D45F` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 1871 | `𝑠` | U+1D460 | cmap | `u1D460` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 1872 | `𝑡` | U+1D461 | cmap | `u1D461` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 1873 | `𝑢` | U+1D462 | cmap | `u1D462` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 1874 | `𝑣` | U+1D463 | cmap | `u1D463` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 1876 | `𝑥` | U+1D465 | cmap | `u1D465` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 1878 | `𝑧` | U+1D467 | cmap | `u1D467` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 2009 | `𝛼` | U+1D6FC | cmap | `u1D6FC` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 2014 | `𝜁` | U+1D701 | cmap | `u1D701` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 2016 | `𝜃` | U+1D703 | cmap | `u1D703` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 2019 | `𝜆` | U+1D706 | cmap | `u1D706` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 2021 | `𝜈` | U+1D708 | cmap | `u1D708` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 2024 | `𝜋` | U+1D70B | cmap | `u1D70B` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 2032 | `𝜓` | U+1D713 | cmap | `u1D713` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 2038 | `𝜙` | U+1D719 | cmap | `u1D719` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 2178 | `𝑽` | U+1D47D | cmap | `u1D47D` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 2183 | `𝒂` | U+1D482 | cmap | `u1D482` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 2185 | `𝒄` | U+1D484 | cmap | `u1D484` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 2188 | `𝒇` | U+1D487 | cmap | `u1D487` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 2191 | `𝒊` | U+1D48A | cmap | `u1D48A` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 2193 | `𝒌` | U+1D48C | cmap | `u1D48C` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 2195 | `𝒎` | U+1D48E | cmap | `u1D48E` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 2196 | `𝒏` | U+1D48F | cmap | `u1D48F` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 2197 | `𝒐` | U+1D490 | cmap | `u1D490` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 2198 | `𝒑` | U+1D491 | cmap | `u1D491` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 2201 | `𝒔` | U+1D494 | cmap | `u1D494` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 2202 | `𝒕` | U+1D495 | cmap | `u1D495` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 2205 | `𝒘` | U+1D498 | cmap | `u1D498` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 2206 | `𝒙` | U+1D499 | cmap | `u1D499` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 2208 | `𝒛` | U+1D49B | cmap | `u1D49B` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 2868 | `0` | U+0030 | visual | `glyph02868` | visual: subscript-size digit '0' |
| 2869 | `1` | U+0031 | visual | `glyph02869` | visual: subscript-size digit '1' |
| 2870 | `2` | U+0032 | visual | `glyph02870` | visual: subscript-size digit '2' |
| 2872 | `4` | U+0034 | visual | `glyph02872` | visual: subscript-size digit '4' |
| 2876 | `8` | U+0038 | visual | `glyph02876` | visual: subscript-size digit '8' |
| 2878 | `+` | U+002B | visual | `glyph02878` | visual: plus sign, subscript/small size |
| 2879 | `−` | U+2212 | visual | `glyph02879` | visual: thin flat bar; contextually a minus sign between two subscript tokens (e.g. 'r_1 − 2') |
| 2911 | `a` | U+0061 | visual | `glyph02911` | visual: subscript-size italic 'a' (alternate) |
| 2912 | `b` | U+0062 | visual | `glyph02912` | visual: subscript-size italic 'b' |
| 2913 | `c` | U+0063 | visual | `glyph02913` | visual: subscript-size italic 'c' (alternate) |
| 2914 | `d` | U+0064 | visual | `glyph02914` | visual: subscript-size italic 'd' (alternate) |
| 2919 | `i` | U+0069 | visual | `glyph02919` | visual: subscript-size italic 'i' (alternate) |
| 2923 | `m` | U+006D | visual | `glyph02923` | visual: subscript-size italic 'm' (alternate) |
| 2928 | `r` | U+0072 | visual | `glyph02928` | visual: subscript-size italic 'r' (alternate) |
| 2929 | `s` | U+0073 | visual | `glyph02929` | visual: subscript-size italic 's' (alternate) |
| 2930 | `t` | U+0074 | visual | `glyph02930` | visual: subscript-size italic 't' (alternate) |
| 3002 | `A` | U+0041 | visual | `glyph03002` | visual: subscript-size italic 'A' |
| 3004 | `C` | U+0043 | visual | `glyph03004` | visual: subscript-size italic 'C' |
| 3005 | `D` | U+0044 | visual | `glyph03005` | visual: subscript-size italic 'D' |
| 3009 | `H` | U+0048 | visual | `glyph03009` | visual: subscript-size italic 'H' |
| 3013 | `L` | U+004C | visual | `glyph03013` | visual: subscript-size italic 'L' |
| 3019 | `R` | U+0052 | visual | `glyph03019` | visual: subscript-size italic 'R' |
| 3021 | `T` | U+0054 | visual | `glyph03021` | visual: subscript-size italic 'T' |
| 3023 | `V` | U+0056 | visual | `glyph03023` | visual: subscript-size italic 'V' |
| 3028 | `a` | U+0061 | visual | `glyph03028` | visual: subscript-size italic 'a' |
| 3029 | `b` | U+0062 | visual | `glyph03029` | visual: subscript-size italic 'b' (alternate) |
| 3030 | `c` | U+0063 | visual | `glyph03030` | visual: subscript-size italic 'c' |
| 3031 | `d` | U+0064 | visual | `glyph03031` | visual: subscript-size italic 'd' |
| 3032 | `e` | U+0065 | visual | `glyph03032` | visual: subscript-size italic 'e' |
| 3034 | `g` | U+0067 | visual | `glyph03034` | visual: subscript-size italic 'g' |
| 3036 | `i` | U+0069 | visual | `glyph03036` | visual: subscript-size italic 'i' |
| 3037 | `j` | U+006A | visual | `glyph03037` | visual: subscript-size italic 'j' |
| 3039 | `l` | U+006C | visual | `glyph03039` | visual: subscript-size italic 'l' |
| 3040 | `m` | U+006D | visual | `glyph03040` | visual: subscript-size italic 'm' |
| 3041 | `n` | U+006E | visual | `glyph03041` | visual: subscript-size italic 'n' |
| 3042 | `o` | U+006F | visual | `glyph03042` | visual: subscript-size italic 'o' |
| 3043 | `p` | U+0070 | visual | `glyph03043` | visual: subscript-size italic 'p' |
| 3045 | `r` | U+0072 | visual | `glyph03045` | visual: subscript-size italic 'r' |
| 3046 | `s` | U+0073 | visual | `glyph03046` | visual: subscript-size italic 's', no cmap entry |
| 3047 | `t` | U+0074 | visual | `glyph03047` | visual: subscript-size italic 't' |
| 3048 | `u` | U+0075 | visual | `glyph03048` | visual: subscript-size italic 'u' |
| 3049 | `v` | U+0076 | visual | `glyph03049` | visual: subscript-size italic 'v' |
| 3051 | `x` | U+0078 | visual | `glyph03051` | visual: subscript-size italic 'x' |
| 3053 | `z` | U+007A | visual | `glyph03053` | visual: subscript-size italic 'z' |
| 3090 | `λ` | U+03BB | visual | `glyph03090` | visual: greek small lambda |
| 3095 | `π` | U+03C0 | visual | `glyph03095` | visual: greek small pi |
| 3096 | `ρ` | U+03C1 | visual | `glyph03096` | visual: greek small rho |
| 3117 | `1` | U+0031 | visual | `glyph03117` | visual: subscript-size digit '1' (alternate) |
| 3118 | `2` | U+0032 | visual | `glyph03118` | visual: subscript-size digit '2' (alternate) |
| 3276 | `a` | U+0061 | visual | `glyph03276` | visual: subscript-size italic 'a' (alternate) |
| 3278 | `C` | U+0043 | visual | `glyph03278` | visual: subscript-size italic 'C' (alternate) |
| 3284 | `i` | U+0069 | visual | `glyph03284` | visual: subscript-size italic 'i' (alternate) |
| 3288 | `m` | U+006D | visual | `glyph03288` | visual: subscript-size italic 'm' (alternate) |
| 3289 | `n` | U+006E | visual | `glyph03289` | visual: subscript-size italic 'n' (alternate) |
| 3290 | `o` | U+006F | visual | `glyph03290` | visual: subscript-size italic 'o' (alternate width) |
| 3291 | `p` | U+0070 | visual | `glyph03291` | visual: subscript-size italic 'p' (alternate width) |
| 3293 | `r` | U+0072 | visual | `glyph03293` | visual: subscript-size italic 'r' (alternate) |
| 3299 | `x` | U+0078 | visual | `glyph03299` | visual: subscript-size italic 'x' (alternate) |
| 3397 | `+` | U+002B | cmap | `plus` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 3398 | `−` | U+2212 | cmap | `minus` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 3400 | `×` | U+00D7 | cmap | `multiply` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 3404 | `=` | U+003D | cmap | `equal` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 3409 | `≤` | U+2264 | cmap | `lessequal` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 3410 | `≥` | U+2265 | cmap | `greaterequal` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 3415 | `/` | U+002F | visual | `glyph03415` | visual: plain diagonal slash; contextual usage '≤12/h' implies unit fraction slash |
| 3435 | `(` | U+0028 | visual | `glyph03435` | visual: large/stretched left parenthesis |
| 3436 | `(` | U+0028 | visual | `glyph03436` | visual: medium stretched left parenthesis |
| 3439 | `)` | U+0029 | visual | `glyph03439` | visual: large/stretched right parenthesis |
| 3440 | `)` | U+0029 | visual | `glyph03440` | visual: medium stretched right parenthesis |
| 3493 | `√` | U+221A | visual | `glyph03493` | visual: square-root sign, standard size |
| 3495 | `√` | U+221A | visual | `glyph03495` | visual: tall/stretched square-root stroke (no attached vinculum glyph found separately in this doc) |
| 3533 | `Σ` | U+03A3 | visual | `glyph03533` | visual: capital sigma (large summation operator) |
| 4662 | `̇` | U+0307 | cmap | `uni0307` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 4666 | `(` | U+0028 | cmap | `parenleft` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 4667 | `)` | U+0029 | cmap | `parenright` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 4670 | `[` | U+005B | cmap | `bracketleft` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 4671 | `]` | U+005D | cmap | `bracketright` | rezolvat direct din tabela cmap proprie a fontului Cambria Math (GID -> nume glif -> Unicode), presupunand ca CID-ul din PDF == GID-ul din fontul original sub Identity-H/CIDFontType0 |
| 4672 | `(` | U+0028 | visual | `glyph04672` | visual: small stretched left parenthesis |
| 4673 | `)` | U+0029 | visual | `glyph04673` | visual: small stretched right parenthesis |
| 4678 | `(` | U+0028 | visual | `glyph04678` | visual: largest stretched left parenthesis |
| 4679 | `)` | U+0029 | visual | `glyph04679` | visual: largest stretched right parenthesis |
