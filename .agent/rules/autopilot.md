---
trigger: always_on
---

# Autopilot Rules (DocIntelRAG)

- Devi leggere SEMPRE `docs/AppRequirements.md` e `docs/TestPlan.md` prima di proporre modifiche architetturali o scrivere codice.
- L’obiettivo è: implementare l’app e far passare TUTTI i test definiti in `docs/TestPlan.md`, includendo soglie di performance/accuracy sul golden set.
- Scelte tecniche MVP (vincolanti salvo motivi forti):
  - Backend: Python + FastAPI
  - Job async: Celery + Redis
  - DB: PostgreSQL (con estensione vettoriale pgvector)
  - Frontend: React + Vite
  - E2E: Playwright
  - Unit test: Pytest + coverage
- Ogni feature deve avere:
  - test unit/integration corrispondenti
  - log e gestione errori
- Se un test fallisce:
  - non “bypassare” il test
  - correggere il bug e rieseguire la suite
- Output sempre tracciabile: quando estrai campi, conserva evidence (pagina e, se possibile, bbox).
- La chat RAG deve usare riconciliazione per domande di completezza ordine/consegna (non rispondere a fantasia).
