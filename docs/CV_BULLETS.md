# Bullets CV / portofoliu — NormativAI

Extrase din decizii și rezultate reale ale proiectului, nu generice. Fiecare bullet are o
variantă scurtă (CV) și, dedesubt, contextul complet (pentru interviu, dacă se cere detaliu).

## Performanță

**Am identificat și rezolvat un bottleneck care făcea importul de date de 38 de minute
pentru 5778 de documente, reducându-l la o estimare sub 5 minute prin batching, cu
verificarea limitelor reale ale API-ului (nu presupuse) și garanții explicite de ordine.**

> Măsurasem doar 29 de secunde de CPU în cele 38 de minute — restul era latență de rețea,
> dintr-un apel separat per fragment către API-ul de embeddings. Am verificat direct în
> documentația oficială limitele reale per cerere (1000 texte / 320.000 tokeni, nu
> valoarea din biblioteca client, care era altceva) și am scris un algoritm de grupare pe
> felii consecutive care respectă ambele simultan. Cel mai riscant mod de eșec — o
> inversare silențioasă între embedding și fragment, care ar fi corupt căutarea semantică
> fără nicio eroare vizibilă — l-am acoperit cu teste explicite pe granița dintre loturi,
> cu embeddings distincte și verificabile per text.

## Corectitudine / calitate a datelor

**Am găsit și corectat o eroare de codificare Unicode (sedilă vs. virgulă pe ț/ș) care
afecta peste 27.000 de caractere în șase documente și strica silențios potrivirea exactă
la căutare — fără nicio eroare vizibilă, doar rezultate lipsă.**

> Soluția a fost strict limitată la cele patru perechi de caractere afectate (nu o
> normalizare Unicode globală, care ar fi stricat simboluri matematice reconstruite din
> PDF-uri), aplicată simetric la ingestie și la interogare — altfel aș fi mutat problema
> de pe server pe utilizator, nu aș fi rezolvat-o.

## Extracție de date netriviale

**Am reconstruit formule matematice din PDF-uri cu fonturi embedded fără tabel
`/ToUnicode`, care produceau caractere aleatorii (silabe etiopiene, cifre tamile) la
extragerea standard — folosind geometria glifelor și un algoritm de învățare prin
interpolare pentru cazurile fără potrivire directă.**

> Nu am ghicit niciodată un glif necunoscut: fiecare caracter needentificat rămâne marcat
> explicit în text, ușor de găsit și raportat, în loc să fie aproximat silențios.

## Securitate / control acces

**Am proiectat controlul de acces anonim (quota 10 întrebări/browser + rate limiting per
IP) cu fail-closed pe toată configurația și cu izolare corectă a bugetului zilnic de
costuri față de restul tranzacției.**

> O reservare de buget pe o conexiune DB separată de restul cererii, ca numărul de apeluri
> plătite să rămână corect chiar dacă restul cererii eșuează și face rollback după ce banii
> erau deja cheltuiți. RLS activ pe fiecare tabel din prima migrare care îl creează, fără
> politici — deny-all pentru rolurile publice, FastAPI fiind singurul client DB.

## Fiabilitate anti-hallucination

**Am proiectat un pipeline RAG care refuză explicit să răspundă fără dovezi și validează
fiecare citare a modelului împotriva fragmentelor efectiv trimise, înainte să ajungă la
utilizator.**

> Claude nu e apelat deloc dacă nu există dovezi (economie directă de cost, nu doar
> corectitudine). Orice citare care nu corespunde unui ID de dovadă furnizat respinge
> răspunsul, nu îl afișează parțial.

## Disciplină de testare

**413 teste locale, complet mockuite — zero cost, zero apeluri externe la rulare standard
— acoperind explicit cele mai periculoase moduri de eșec silențios (inversare de ordine,
scurgere de identificatori tehnici, import parțial), nu doar fericitul caz.**

---

*Notă: numerele (5778 fragmente, 27.000+ caractere, 413 teste) sunt din stare curentă a
proiectului la 04-09-2026; actualizează-le dacă le folosești mai târziu.*
