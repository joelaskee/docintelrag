# DocIntelRAG — Application Requirements Specification (v1.1)

## 0. Visione e obiettivo

Realizzare una piattaforma **self-hosted, cross-platform (Linux + Windows)** che consenta a un’azienda di:

- ingerire una cartella di documenti PDF (nativi o scansionati)
- estrarre il contenuto testuale nel modo più fedele possibile
- trasformare i contenuti in dati strutturati e semanticamente etichettati
- consentire verifica, correzione e validazione umana
- interrogare i documenti tramite AI (RAG) e dashboard di Business Intelligence
- supportare controlli incrociati tra documenti (es. Ordini vs DDT)

La piattaforma deve privilegiare **affidabilità, spiegabilità e controllo umano**, non automazione cieca.

---

## 1. Principi guida (vincolanti)

- **Human-in-the-loop by design**: l’utente può sempre correggere.
- **Local-first**: nessun invio di documenti o contenuti a servizi cloud esterni per default.
- **Explainability**: ogni dato estratto deve essere tracciabile alla sua origine.
- **Onestà del sistema**: in caso di ambiguità o bassa confidenza, il sistema deve segnalarlo.
- **Multi-tenant isolation**: i dati di un cliente non devono mai contaminare altri tenant.
- **Cross-platform reale**: l’applicazione deve funzionare su Windows e Linux senza modifiche funzionali.

---

## 2. Ruoli utente (RBAC)

### Admin
- Configura tenant, utenti e ruoli
- Definisce schemi di estrazione e KPI
- Gestisce impostazioni OCR, LLM, embedding
- Può correggere e validare qualsiasi dato
- Accede ai log di audit

### Operatore
- Avvia ingestione documenti
- Revisiona e corregge dati estratti
- Valida documenti

### Manager
- Interroga il sistema via chatbot
- Consulta dashboard BI
- Non può modificare dati o configurazioni

---

## 3. Modalità di ingestione documenti

Devono essere supportate **entrambe** le modalità:

### A) Upload cartella (browser)
- Selezione cartella locale
- Upload multiplo PDF
- Stato job visibile (queued / running / failed / completed)

### B) Cartella server (path)
- Inserimento path server consentito (allowlist)
- Scansione ricorsiva
- Prevenzione path traversal

### Requisiti comuni
- Deduplica tramite hash
- Versionamento documenti (opzionale ma tracciabile)
- Job asincroni (UI non bloccante)
- Log comprensibili per utente non tecnico

---

## 4. Classificazione documento

Il sistema deve classificare ogni PDF in una delle seguenti categorie:

- Ordine (PO)
- Documento di Trasporto / Bolla (DDT)
- Fattura
- Altro / Non classificato

Requisiti:
- Classificazione automatica con confidenza
- Override manuale persistente
- Classificazione ambigua ammessa e segnalata

---

## 5. Estrazione testo (fidelity-first)

### PDF nativi
- Estrazione diretta text-layer
- Preservazione ordine logico
- Supporto tabelle quando possibile
- Riferimento pagina per ogni blocco

### PDF scansionati
- OCR automatico
- Pre-processing immagini se necessario
- Segnalazione qualità OCR
- Timeout e fallback controllati

### Output minimo per documento
- raw_text
- testo per pagina
- blocchi con riferimento pagina (bbox se disponibile)
- warning (OCR bassa qualità, layout complesso, ecc.)

---

## 6. Meta-tagging e strutturazione dati

Il sistema deve estrarre dati strutturati dai documenti, tra cui:

### Entità principali
- Fornitore (ragione sociale, P.IVA, indirizzo)
- Documento (numero, data, tipo)
- Righe articolo (codice, descrizione, quantità, UM, prezzo)

### Requisiti
- Ontologia configurabile per tenant
- Estrazione ibrida:
  - regole deterministiche
  - supporto LLM (se disponibile)
- Ogni campo deve avere:
  - valore raw
  - valore normalizzato
  - confidenza
  - evidence (pagina / riferimento)

---

## 7. Human-in-the-loop (obbligatorio)

Per ogni documento deve esistere una UI di revisione che consenta:

- visualizzazione PDF
- evidenziazione evidenze
- modifica manuale campi/tag
- salvataggio eventi di modifica
- audit trail completo

Le correzioni umane devono poter migliorare estrazioni successive (per tenant).

---

## 8. Dataset strutturato e BI

I dati devono essere persistiti in forma **BI-ready**, includendo:

- documenti
- fornitori
- ordini
- DDT
- fatture
- righe articolo
- eventi di modifica

Requisiti:
- query SQL read-only
- export CSV/Parquet
- KPI configurabili per tenant

---

## 9. Motore di riconciliazione documentale

Il sistema deve supportare controlli incrociati, in particolare:

### Ordine ↔ DDT
- match automatico (numero, fornitore, riferimenti)
- supporto consegne parziali e multiple
- segnalazione articoli mancanti o extra
- stato: COMPLETO / PARZIALE / AMBIGUO

Ogni risultato deve essere spiegabile e tracciabile.

---

## 10. Chatbot RAG (Knowledge Base)

- Interrogazione in linguaggio naturale
- Retrieval su contenuti documentali del tenant
- Risposte con citazioni (documento + pagina)
- Routing intelligente:
  - domande di riconciliazione → motore dedicato
  - domande informative → RAG standard
- LLM locale via Ollama (default)

---

## 11. Dashboard BI

- Vista dashboard con KPI configurabili
- Widget base (card, trend, tabelle)
- Filtri per periodo, fornitore, tipo documento
- Drilldown verso documenti e righe

---

## 12. UI/UX (utente non tecnico)

Sezioni minime:
1. Ingestion
2. Documenti
3. Revisione documento
4. Chat AI
5. Dashboard
6. Admin (solo per admin)

La UI deve privilegiare:
- chiarezza
- feedback immediato
- assenza di gergo tecnico

---

## 13. Requisiti non funzionali

- Deployment:
  - Docker Compose per server
  - Accesso via browser (Windows/Linux)
- Porte di servizio non standard (configurabili)
- Sicurezza:
  - autenticazione
  - RBAC
  - audit log
- Performance:
  - ingest asincrono
  - risposta chatbot < 10s su dataset medio
- Osservabilità:
  - log strutturati
  - metriche base

---

## 14. Fuori scope (v1)

- Integrazione diretta ERP
- Conservazione sostitutiva
- Firma digitale
- Training ML avanzato

---

## 15. Criterio di successo

L’applicazione è considerata conforme se:
- tutti i requisiti funzionali sono implementati
- il TestPlan è completamente soddisfatto
- il sistema gestisce ambiguità senza inventare
- l’utente mantiene sempre il controllo finale
