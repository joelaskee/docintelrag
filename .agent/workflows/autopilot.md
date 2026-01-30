---
description: Build DocIntelRAG end-to-end (scaffold, implement, test, iterate until green)
---

0. Pre-check
   - verifica Docker, Node, Python
   - verifica OCR engine presente (es. tesseract --version)
   - verifica Ollama in ascolto e modello disponibile (ollama list)
   - se manca qualcosa: installa / stampa istruzioni e procede con fallback

1. Read specs
   - Open and summarize `docs/AppRequirements.md` and `docs/TestPlan.md`.
   - Produce an Implementation Plan artifact and a Task List.

2. Scaffold project
   - Create backend (FastAPI) + frontend (React/Vite) + docker-compose (postgres, redis).
   - Add CI config to run: lint, unit, integration, e2e.

3. Implement MVP vertical slice
   - Ingestion (upload folder) -> store PDF -> extract text -> persist document record.
   - Document list UI + doc detail page.

4. Add OCR routing
   - Detect scanned PDFs and run OCR pipeline.
   - Store OCR outputs and evidence metadata.

5. Add meta-tagging + human loop
   - Implement schema-based extraction with confidence + evidence.
   - Add correction UI + persist field_events.

6. Add RAG + reconciliation
   - Build vector index per tenant.
   - Implement reconciliation PO vs DDT and wire chatbot to use it when needed.

7. Add Dashboard
   - KPI widgets + admin configuration + drilldown.

8. Tests & quality gates
   - Create `testdata/` and golden expected JSON.
   - Implement accuracy checks and performance smoke tests.
   - Run full test suite. If anything fails, fix and repeat this step until green.

9. Final artifacts
   - Generate `docs/STATUS.md` with: features done, how to run, how to test, known limits.
   - Generate a short walkthrough (screenshots if available).