# R08 — raport Coder

## Implementare
Contractul intern `Evidence` include `chunk_order` cu default `0`. Query-urile repository selectează `chunk.chunk_order`, iar rândurile actuale îl transmit spre evidence: exact are 9 câmpuri, semantic are 10 (ultimul este score).

Pentru compatibilitate cu fixture-urile mock legacy, repository-ul acceptă în continuare rânduri fără `chunk_order`: 8 câmpuri pentru exact și 9 pentru semantic. În acest caz, folosește `chunk_id` drept ordine deterministă numai în memory/test fixtures. Rândurile reale cu `chunk_order` folosesc întotdeauna valoarea DB.

`_has_ambiguous_article` deduplică hash-uri identice și verifică pozițiile distincte: chunk-uri consecutive sunt acceptate; poziție duplicată sau gap rămâne `ambiguous_article`.

## Teste actualizate
- query exact și semantic verifică prezența `chunk.chunk_order` și maparea acestuia;
- mock-uri legacy exact/semantic verifică fallback-ul deterministic fără `IndexError`;
- exact: două chunk-uri consecutive ale aceluiași articol sunt `found`;
- semantic: două chunk-uri consecutive ale aceluiași articol sunt `found`;
- exact: poziție duplicate cu hash-uri diferite rămâne `ambiguous_article`;
- semantic: gap în ordine rămâne `ambiguous_article`.

## Validare
Plannerul a raportat eșecuri API pre-remediere: 69 `IndexError` pentru fixture-uri cu 8/9 câmpuri. Nu au fost rulate comenzi de Coder, conform constrângerii; este necesară rularea de către Tester/QA.

## Riscuri reziduale
În semantic search, top-k poate conține doar o parte neconsecutivă dintr-un articol lung, ceea ce este tratat fail-closed ca ambiguitate conform deciziei aprobate. Nu au fost atinse schema DB, providerii, deployment-ul sau statusurile documentelor.
