# R07 — audit securitate release

## Sarcină
Audit read-only pentru readiness production: endpoint-uri, autentificare/autorizare, rate limiting, CORS, secrete/logging, acces DB și rute administrative.

## Context
NormativAI are 11 documente approved. Nu există autorizare pentru schimbări, deploy, DB write sau apeluri plătite.

## Rezultat așteptat
Verdict production gate: PASS/BLOCKED, finding-uri prioritizate cu fișier/linie și dovezi. Spune explicit ce nu poate fi verificat static.

## Constrângeri
Read-only. Nu rula comenzi, nu edita fișiere, nu expune secrete, nu presupune starea Railway/Supabase.
