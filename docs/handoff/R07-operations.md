# R07 — audit operațional release

## Sarcină
Audit read-only pentru readiness production: CI, deploy, health/smoke, rollback, backup/restore, observabilitate, documentație operațională și paritate main/Railway.

## Context
NormativAI are 11 documente approved. Nu există autorizare pentru schimbări, deploy, DB write sau apeluri plătite.

## Rezultat așteptat
Verdict production gate: PASS/BLOCKED, finding-uri prioritizate cu fișier/linie și dovezi. Spune explicit ce necesită verificare externă.

## Constrângeri
Read-only. Nu rula comenzi, nu edita fișiere, nu expune secrete, nu presupune starea Railway/Supabase.
