# Tokeni de design — NormativAI

Sursă: valori **măsurate** (computed styles) de pe `https://ai.acquisition.com/` la 04-09-2026,
paleta de referință aprobată de Lucian. Nu sunt ghicite și nu sunt copiate din `:root` —
variabilele `:root` ale site-ului sunt tema light implicită shadcn și **nu** reflectă ce se
randează efectiv. Valorile de mai jos vin din `getComputedStyle` pe pagina redată în dark mode.

## Culori

| Rol | Valoare | Note |
|---|---|---|
| Fundal de bază | `#131628` | `rgb(19, 22, 40)` |
| Fundal body | `#161A27` | `rgb(22, 26, 39)` |
| Gradient peste conținut | `linear-gradient(rgba(109,40,217,.25), rgba(162,28,175,.20), rgba(55,48,163,.25))` | violet → fucsia → indigo; dă tenta violet a paginii |
| Accent / primary | `#811AFF` | `hsl(267 100% 50%)` — „acquisition purple” |
| Accent, fundal difuz | `rgba(129, 26, 255, 0.10)` | pentru iconițe și stări active |
| Text principal | `#FAFAFA` | |
| Text titluri | `#FFFFFF` | |
| Text secundar | `#A6A6A6` | |
| Text secundar (alt) | `rgba(255, 255, 255, 0.70)` | |
| Suprafață card | `rgba(255, 255, 255, 0.05)` | |
| Bordură subtilă | `rgba(255, 255, 255, 0.10)` | pe carduri |
| Bordură solidă | `#363B49` | separator footer |

## Tipografie

- Familie: **Poppins**, fallback `system-ui, sans-serif`.
- Bază: `16px`.
- `h1`: `60px` / line-height `60px`, weight `700`, letter-spacing `-1.5px`.
- Butoane și linkuri UI: `14px`, weight `500`.

## Formă

- Raze: **6px** (butoane, inputuri), **8px** (implicit, `--radius: .5rem`), **12px** (carduri).
- Padding card: `24px`.
- CTA: fundal `#811AFF`, text `#FAFAFA`, rază `6px`, padding `0 32px`, weight `500`, `14px`, fără umbră.
- Footer: fundal transparent, `border-top: 1px solid #363B49`.
- Fără `box-shadow` pe carduri și CTA — separarea se face prin bordură și suprafață, nu prin umbră.

## Ce NU se preia

- Logo-ul, numele și textele Acquisition.com. Se preia **doar sistemul vizual**, nu identitatea.
- Tema light a site-ului de referință. NormativAI pornește dark-only în această iterație.

## Avertisment: Poppins și GDPR

Poppins este un Google Font. Încărcarea lui de pe `fonts.googleapis.com` trimite IP-ul
vizitatorului către Google, ceea ce **adaugă un procesator terț** ce nu apare acum în
`static/confidentialitate.html`. Două opțiuni, ambele acceptabile:

1. **Self-hosting** fontului din proiect (recomandat) — fără terț nou, fără modificarea politicii;
2. păstrarea CDN-ului Google și **completarea explicită** a politicii de confidențialitate.

Decizia îi aparține lui Lucian și trebuie luată înainte de implementare.
