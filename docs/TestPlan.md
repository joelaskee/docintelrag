# DocIntelRAG — Test Plan & Verification (v1.1)

## Test Philosophy

- I test verificano affidabilità, coerenza, tracciabilità e robustezza del sistema, non la perfezione semantica assoluta.
- In presenza di ambiguità nei documenti, il comportamento corretto è:
  - segnalare bassa confidenza
  - rendere evidente l’ambiguità
  - consentire intervento umano
- L’assenza di crash, la spiegabilità tramite evidence (documento/pagina/bbox) e la possibilità di correzione manuale
  sono considerate esito positivo del test.
- I test non devono mai forzare l’uso di OCR o LLM quando non necessario.
- I test di volume e carico devono essere implementati tramite simulazione (mock/stub) e NON tramite elaborazione reale massiva.

---

## Classificazione dei test

- **[REAL]** → usa documenti reali del golden set
- **[MOCK]** → usa simulazioni, stub o repliche logiche
- **[HUMAN]** → ammette o richiede intervento umano

---

## 0. Obiettivo test

Verificare:
- correttezza e fedeltà dell’estrazione testo/OCR
- correttezza del meta-tagging e della riconciliazione documentale
- funzionamento dei flussi principali UI
- prestazioni minime accettabili
- robustezza del sistema in caso di errori o ambiguità
- rispetto dei vincoli di sicurezza, RBAC e isolamento tenant

---

## 1. Ambienti di test

- **Dev**: Docker Compose locale, dataset ridotto
- **CI**: esecuzione automatica test (unit + integration + e2e)
- **Staging**: ambiente simile a produzione con dataset realistico

---

## 2. Test data (Golden Set) [REAL]

Cartella `testdata/` con:

### `testdata/input/`
- 1 Ordine (PO) PDF nativo
- 1 DDT PDF nativo completo
- 1 DDT PDF nativo parziale
- 1 Fattura PDF nativa
- 1 PDF scansionato qualità media
- 1 PDF scansionato qualità bassa

### `testdata/expected/`
Per ogni documento un file JSON contenente:
- tipo documento atteso
- entità principali attese (P.IVA, numero, data, fornitore)
- righe articolo attese (codice, quantità minime)
- relazioni attese (PO ↔ DDT ↔ Fattura)

---

## 3. Metriche di qualità estrazione

### OCR [REAL]
- Scansione qualità media:
  - Character Error Rate (CER) stimato ≤ 5%
- Scansione qualità bassa:
  - non è richiesto il rispetto di una soglia CER
  - il sistema deve segnalare bassa qualità/confidenza

### Estrazione campi strutturati [REAL]
- Campi forti (P.IVA, numero documento, data):
  - accuratezza ≥ 95% sul golden set
- Righe articolo (codice + quantità):
  - accuratezza ≥ 90% sul golden set

---

## 4. Test funzionali (Acceptance)

### 4.1 Ingestion

- **[REAL] F1**: ingest di cartella con PDF reali → job completato, documenti visibili
- **[MOCK] F2**: ingest di N documenti simulati → pipeline stabile, nessun crash
- **[REAL] F3**: deduplica → stesso PDF non crea duplicati (o nuova versione secondo policy)

---

### 4.2 OCR routing

- **[REAL] F4**: PDF nativo non passa da OCR
- **[REAL] F5**: PDF scansionato attiva OCR e produce testo + warning qualità

---

### 4.3 Classificazione tipo documento

- **[REAL] F6**: classificazione corretta su golden set
- **[HUMAN] F7**: override manuale tipo documento persistito correttamente

---

### 4.4 Meta-tagging e human-in-the-loop

- **[REAL] F8**: campi estratti con valore, confidenza ed evidence
- **[HUMAN] F9**: modifica manuale campo/tag aggiorna dataset e audit log

---

### 4.5 Riconciliazione Ordine ↔ DDT

- **[REAL] F10**: PO completamente consegnato → stato COMPLETO
- **[REAL] F11**: PO parzialmente consegnato → stato PARZIALE con elenco mancanti
- **[REAL] F12**: articoli in DDT non presenti in PO → segnalati come anomalie
- **[HUMAN] F13**: riferimenti ambigui → stato AMBIGUO, richiesta revisione

---

### 4.6 Chatbot RAG

- **[REAL] F14**: query “è arrivata tutta la merce dell’ordine X?”:
  - invoca riconciliazione
  - risponde con stato e dettagli
  - cita documenti e pagine
- **[REAL] F15**: query puramente informativa → risposta con citazioni
- **[REAL] F16**: isolamento tenant → nessuna contaminazione dati

---

### 4.7 Dashboard BI

- **[REAL] F17**: KPI base configurabili e visibili
- **[REAL] F18**: drilldown da KPI a lista documenti corretta

---

## 5. Test di performance e carico

### Nota fondamentale sui test di volume

I test che fanno riferimento a N ≥ 50/100 documenti **devono essere implementati come test di carico simulato (mock/stub)**  
e **NON** come elaborazione reale di decine di PDF con OCR.

L’OCR reale è richiesto **solo** sul golden set.

---

### 5.1 Ingestion load [MOCK]

- **[MOCK] P1**: simulazione ingest di 100 documenti:
  - pipeline stabile
  - job scheduling corretto
  - error rate < 2%
  - nessun deadlock

---

### 5.2 Performance OCR reale [REAL]

- **[REAL] P2**: OCR su golden set:
  - scansione media: tempo medio ≤ 15s/documento
  - scansione bassa qualità: timeout gestito correttamente

---

### 5.3 Performance Chat [MOCK]

- **[MOCK] P3**: 50 query simulate:
  - p95 latency ≤ 10s
  - p99 ≤ 20s

---

## 6. Test sicurezza

- **[REAL] S1**: RBAC → operatore non accede a funzioni admin
- **[REAL] S2**: audit log su modifica dati
- **[REAL] S3**: path traversal prevenuto
- **[MOCK] S4**: rate limit endpoint chat

---

## 7. What is NOT a failure

- Campo estratto con bassa confidenza ma correttamente segnalato
- Stato PARZIALE o AMBIGUO nella riconciliazione
- Risposta chatbot che segnala dati mancanti invece di inventare
- Richiesta di revisione umana su documenti di bassa qualità

---

## 8. CI Gate (condizioni di successo)

La pipeline CI è considerata **VERDE** se:
- tutti i test unit, integration ed e2e passano
- le metriche di accuracy del golden set rispettano le soglie
- i test di carico simulato completano senza errori
