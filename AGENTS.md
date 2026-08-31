# Reguli agenți — Omnia

## Scop

Omnia este numele intern al proiectului/repository-ului; brandul public al aplicației este **NormativAI**. Proiectul este simultan produs vandabil și material de portofoliu/CV. Prioritatea este corectitudinea, trasabilitatea surselor și siguranța costurilor.

## Reguli de lucru

1. Comunică în română, clar și concis.
2. Explică orice cod nou sau modificat linie cu linie, la nivel de începător.
3. Marchează explicit valoarea de CV a deciziilor relevante.
4. Un singur obiectiv clar per task/sesiune.
5. Nu accepta automat editări: prezintă planul și diff-ul înainte de schimbări importante.
6. Nu expune sau tipări secrete, tokenuri, parole sau conținut din `.env`.
7. Nu comite documente normative, PDF-uri, texte extrase sau chei API. `documente_noi/` rămâne exclus din Git.
8. Nu face `git push`, deploy, migrare Supabase sau apeluri API plătite fără aprobarea explicită a lui Lucian.
9. Nu slăbi, șterge sau restrânge teste doar pentru a le face să treacă.
10. Actualizează `TASKS.md` la predarea unui task și `PLAN.md` numai când se schimbă o decizie de produs/tehnică aprobată.

## Roluri

- **Planner:** planifică, verifică arhitectura și coordonează; nu editează în afara sarcinii aprobate.
- **Coder:** implementează un task aprobat într-un worktree separat.
- **Reviewer/QA:** read-only; verifică diff-ul, testele, citările, costurile și securitatea.

Nu lăsa doi agenți să editeze aceeași zonă sau Supabase simultan.

## Cerințe Omnia

- Răspunsurile trebuie bazate exclusiv pe context recuperat și să indice documentul/articolul oficial.
- Numele tehnice de sursă nu ajung la client.
- Clientul nu are niciodată acces direct la Supabase, chunk-uri, texte normative sau fișiere originale și nu există endpoint de download. Ingestion-ul este exclusiv decis și executat de Lucian prin backend-ul administrativ.
- Testele implicite folosesc mock-uri; testele API plătite sunt opt-in.
- Pentru schimbări Supabase, urmează skill-urile locale `.agents/skills/supabase` și `.agents/skills/supabase-postgres-best-practices`.
