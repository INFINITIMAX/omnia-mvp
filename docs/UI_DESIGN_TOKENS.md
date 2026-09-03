# Tokeni de design — NormativAI

Direcție **aprobată de Lucian la 04-09-2026**, validată pe mockup vizual.

Înlocuiește complet paleta violet derivată din `ai.acquisition.com`, explorată pe 03-09-2026
și abandonată. Nu mai folosi acele valori nicăieri.

## Concept

Două straturi vizuale distincte, cu roluri diferite:

1. **Carcasa aplicației** este o interfață modernă întunecată: nav lateral stânga, chat box
   rotunjit, gradiente difuze. Registrul este cel al unei aplicații AI contemporane.
2. **Răspunsul** este cules ca un document tipărit. Serif, text justificat cu despărțire în
   silabe, secțiuni numerotate, citări `[1]`/`[2]` și o listă de surse la final.

Distincția este intenționată. Prototipul „Technical Paper” respins pe 03-09-2026 a eșuat
tocmai pentru că a transformat **toată** aplicația în hârtie, în light mode, fără nav lateral
și fără gradiente, adică inversul a ceea ce se ceruse.

## Culori

### Fundal

| Token | Valoare | Rol |
|---|---|---|
| `--ink-900` | `#0A0907` | fundalul paginii, negru cu tentă caldă |
| `--ink-850` | `#100E0B` | foaia răspunsului, varianta închisă |
| `--ink-800` | `#16130F` | fundal composer |
| `--ink-750` | `#1C1813` | element activ în nav |
| `--ink-700` | `#241F18` | suprafață ridicată |

Gradientul de fundal:

```css
radial-gradient(1100px 620px at 8% -12%, rgba(232,185,49,.075), transparent 60%),
linear-gradient(180deg, #0D0B08 0%, #0A0907 46%, #070605 100%)
```

Negrul are bias cald deliberat. Un gri neutru ar bate în albastru sub accentul auriu.

### Accent

| Token | Valoare | Rol |
|---|---|---|
| `--gold` | `#E8B931` | accent principal |
| `--gold-hi` | `#FFD75E` | hover, inel de focus |
| `--gold-deep` | `#7A5D00` | accent pe fundal deschis, capăt de gradient |

Auriu, nu galben-semnal. Galbenul pur pe negru citește ca bandă de avertizare, ceea ce pentru
o aplicație de normative de construcții ar fi o asociere greșită.

### Text

| Token | Valoare | Contrast pe `--ink-900` |
|---|---|---|
| `--paper` | `#F2EEE4` | ~17:1 |
| `--paper-dim` | `#B7AF9D` | ~9:1 |
| `--paper-quiet` | `#9E957F` | 6.7:1 |
| `--gold` pe fundal | `#E8B931` | ~10.7:1 |

Nicio culoare de text sub 4.5:1. Etichetele mono nu coboară sub 11px.

**Corecție măsurată la 04-09-2026, în așteptarea confirmării lui Lucian.** Valoarea inițială
`--paper-quiet: #8E8674` dă 5,51:1 pe `--ink-900` pur, dar fundalul real nu este `--ink-900`
pur: peste el se compun vârful gradientului liniar (`#0D0B08`) și haloul auriu
(`rgba(232,185,49,.075)`), iar în nav se mai adaugă gradientul propriu (`.05`). Pe fundalul
efectiv cel mai deschis rezultat (`#27200D`), `#8E8674` coboară la **4,48:1**, adică sub
pragul AA cerut explicit. `#9E957F` urcă aceeași pereche la **5,44:1** și păstrează 6,69:1 pe
`--ink-900`. Restul paletei rămâne neschimbat.

### Linii

| Token | Valoare | Rol |
|---|---|---|
| `--rule` | `#241F18` | borduri, separatoare |
| `--rule-lit` | `#3A3225` | linii în interiorul documentului |

## Tipografie

| Rol | Familie | Folosire |
|---|---|---|
| Interfață | **Archivo** 400/500/600 | nav, butoane, întrebare, composer |
| Document | **Crimson Pro** 400/600 | corpul răspunsului, articole citate, titluri de secțiune |
| Etichete și coduri | **IBM Plex Mono** 400/500 | etichete majuscule, numere de articol, coduri document, contoare |

Crimson Pro este cea mai apropiată rudă liberă a lui Computer Modern, fontul LaTeX. Archivo
este o grotescă cu caracter instituțional, potrivită pentru semnalistică și documente oficiale.

Scară: corp document `19.5px/1.7`, articol citat `18px/1.62`, titlu secțiune `20px/600`,
întrebare `17px`, interfață `15px`, etichete mono `11px` cu tracking `.13em` până la `.18em`.

Corpul răspunsului este justificat, cu `hyphens: auto`. Măsura utilă rămâne sub 780px.

## Formă și spațiere

Scară unică de spațiere, nimic în afara ei:
`4, 8, 12, 16, 24, 32, 48, 64` px.

| Element | Rază |
|---|---|
| Chat box, butonul de trimitere | `24px` |
| Sigla, elemente de nav | `8px` |
| Foaia răspunsului | `4px` |

Colțurile rotunde aparțin carcasei. **Documentul are colțuri aproape drepte**, deliberat:
contrastul face ca răspunsul să citească drept alt tip de obiect, nu drept încă un card.

Articolele citate se pun ca într-un standard tipărit: linii de păr sus și jos peste toată
măsura, referința agățată în marginea stângă pe o coloană de `96px`, textul în roman.
**Fără bară colorată la stânga, fără card, fără italice.**

## Constrângeri obligatorii (cerute explicit de Lucian, 04-09-2026)

Următoarele sunt interzise în orice mockup sau pagină finală. Lista se aplică integral, nu
selectiv:

- gradient violet spre albastru;
- gradient pe textul titlurilor;
- emoji în titluri;
- Inter peste tot;
- carduri cu bordură colorată la stânga;
- glassmorphism;
- dark mode cu contrast scăzut;
- trei cutii cu iconițe pe un rând;
- badge deasupra titlului;
- iconițe Lucide peste tot;
- componente shadcn nemodificate;
- secțiuni care apar prin fade la scroll;
- fascicul care urmărește cursorul;
- efecte de hover care estompează butoanele;
- spațiere inconsistentă;
- em dash peste tot;
- text generic cu cuvinte la modă;
- italice serif pentru cuvinte accentuate;
- Space Grotesk împreună cu Instrument Serif;
- textură de grain peste gradient.

## Foaia răspunsului (decis 04-09-2026)

Varianta **închisă** este cea aprobată: răspunsul se culege pe `--ink-850`, coerent cu restul
aplicației. Varianta „hârtie”, o foaie crem plutind în carcasa neagră, a fost prototipată și
respinsă. Nu se implementează comutator între cele două.

## Avertisment GDPR

Archivo, Crimson Pro și IBM Plex Mono sunt Google Fonts. Servite de pe `fonts.googleapis.com`,
trimit IP-ul fiecărui vizitator către Google, ceea ce adaugă un procesator terț care nu apare
în `static/confidentialitate.html`. Se rezolvă prin **self-hosting**, cum s-a procedat deja cu
IBM Plex în prototipul anterior. Alternativa este completarea explicită a politicii.
