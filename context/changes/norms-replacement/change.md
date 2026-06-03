---
id: norms-replacement
title: "Wymiana bazy norm (S-04)"
status: implementing
created: 2026-06-01
updated: 2026-06-03
roadmap_ref: S-04
prd_refs: [FR-008]
unlocks: []
---

## Summary

Uzupełnia obsługę FR-008 o brakujące ogniwa: widoczny dialog błędu gdy norms.json
jest niepoprawny lub brakuje (zamiast cichego sys.exit w .exe), tryb CLI
`--validate-norms <path>` dla administratora oraz dokumentację schematu
(norms.json.template + docs/README-norms.md).
