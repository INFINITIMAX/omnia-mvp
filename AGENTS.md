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
9. Pe branch-ul de lucru, creează checkpoint prin commit + push la maximum 25 de minute; nu lucra direct pe `main` și nu folosi force, merge sau deploy.
10. Nu slăbi, șterge sau restrânge teste doar pentru a le face să treacă.
11. Actualizează `TASKS.md` la predarea unui task și `PLAN.md` numai când se schimbă o decizie de produs/tehnică aprobată.
12. Nu introduce implicit comportamente de produs privind eligibilitatea documentelor, statusuri, acces, costuri, quota, fallback-uri sau date publice. Prezintă impactul în limbaj simplu și cere aprobarea explicită a lui Lucian înainte de implementare.
13. Un finding de Reviewer care schimbă comportamentul de produs devine propunere pentru Lucian, nu remediere automată.
14. Înainte de merge, raportează separat: comportamente noi, valori implicite, efecte DB, filtre ascunse, costuri/API și funcționalități încă neconectate.
15. Înregistrează deciziile aprobate în `docs/DECISIONS.md` și menține `docs/PROJECT_OVERVIEW.md` sincronizat cu starea reală.

## Roluri

- **Planner:** planifică, verifică arhitectura și coordonează; nu editează în afara sarcinii aprobate.
- **Coder:** implementează un task aprobat într-un worktree separat.
- **Reviewer/QA:** read-only; verifică diff-ul, testele, citările, costurile și securitatea.

Nu lăsa doi agenți să editeze aceeași zonă sau Supabase simultan.

## Structura fixă de agenți

- Există maximum 4 roluri live: Planner, un singur Coder, un singur Tester/QA și un singur Reviewer.
- Planner-ul coordonează, explică impactul și cere aprobările; nu deleagă deciziile de produs.
- Coder-ul este singurul agent care modifică implementarea task-ului curent.
- Tester/QA rulează testele, verifică ramurile și raportează golurile; rămâne read-only, iar remedierile merg înapoi la Coder.
- Reviewer-ul face review read-only pentru arhitectură, securitate, cost și comportament; nu dublează rolul Testerului.
- Refolosește agenții și worktree-urile rolurilor; nu crea câte un agent nou pentru fiecare fază.
- Fiecare agent primește un singur obiectiv hiperspecializat, pentru a evita poluarea contextului.
- Nu porni subagenți sau consilii din Coder/Tester/Reviewer.
- După predare, închide/release agenții care nu mai au scop; un worktree existent nu justifică un agent idle.

## Cerințe Omnia

- Răspunsurile trebuie bazate exclusiv pe context recuperat și să indice documentul/articolul oficial.
- Numele tehnice de sursă nu ajung la client.
- Clientul nu are niciodată acces direct la Supabase, chunk-uri, texte normative sau fișiere originale și nu există endpoint de download. Ingestion-ul este exclusiv decis și executat de Lucian prin backend-ul administrativ.
- Testele implicite folosesc mock-uri; testele API plătite sunt opt-in.
- Pentru schimbări Supabase, urmează skill-urile locale `.agents/skills/supabase` și `.agents/skills/supabase-postgres-best-practices`.
