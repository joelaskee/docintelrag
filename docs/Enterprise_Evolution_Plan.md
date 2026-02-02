# Enterprise Evolution Plan: DocIntelRAG 2.0 🚀

Questo documento delinea il percorso evolutivo per trasformare DocIntelRAG da un archivio documentale intelligente a una vera **Piattaforma di Controllo di Gestione Automatica**.

## 🎯 Obiettivi Strategici
1.  **Riconciliazione Automatica (3-Way Matching)**: Verificare automaticamente che *ciò che è stato ordinato* = *ciò che è arrivato* = *ciò che è stato fatturato*.
2.  **Analisi Temporale (Trend Analysis)**: Fornire insight sull'andamento dei costi/acquisti nel tempo (Confronti Mese su Mese, Anno su Anno).
3.  **Affidabilità Totale**: Passare da "ricerca" a "certificazione" del dato.

---

## 🏗️ Fase 1: Estrazione Grandulare (Line Items)
Per confrontare i documenti, non bastano i totali. Dobbiamo "leggere" le righe degli articoli.

### 1.1 Nuovi Modelli Dati
- Tabella `document_lines`:
    - `description` (Descrizione articolo)
    - `quantity` (Quantità)
    - `unit_price` (Prezzo unitario - spesso assente nei DDT)
    - `line_total` (Totale riga)
    - `product_code` (Codice articolo fornitore/interno)
    - `unit_measure` (Pz, Kg, m, etc.)

### 1.2 Pipeline di Estrazione Aggiornata
- Aggiornare il prompt System dell'LLM (o usare un tool specifico) per estrarre una lista JSON di righe.
- **Sfida Tecnica**: I DDT sono spesso scansionati male o scritti a mano. Sarà necessario potenziare `deepseek-ocr` o usare modelli specifici per tabelle.

### 1.3 Interfaccia di Validazione ("Data Entry Assistito")
- L'utente deve poter vedere la tabella estratta accanto al PDF e correggere eventuali errori di lettura sulle righe prima di confermare il documento.

---

## ⚖️ Fase 2: Motore di Riconciliazione (The Auditor)
Il cuore del sistema Enterprise. Un motore logico che collega i documenti.

### 2.1 Raggruppamento (Grouping Strategy)
- Identificare il "Filo Rosso": collegare i documenti tramite riferimenti incrociati (es. Fattura cita DDT n.123, DDT cita Ordine n.456).
- Creare l'entità `PurchaseFlow` che raggruppa PO + DDT(s) + Fattura(s).

### 2.2 Algoritmo di Matching
1.  **Check Quantità (DDT vs Ordine)**:
    - La somma delle quantità nei DDT ricevuti copre l'ordine?
    - Alert: "Merce Mancante" (Backorder) o "Merce in Eccesso".
2.  **Check Prezzo (Fattura vs Ordine)**:
    - Il prezzo fatturato corrisponde al prezzo pattuito nell'ordine?
    - Alert: "Variazione Prezzo" (> soglia tolleranza).

### 2.3 Chatbot "Auditor"
- L'utente chiede: *"L'ordine 104 è completo?"*
- Il sistema risponde: *"No, mancano 50 viti. Ordinati 100, arrivati 50 col DDT 22. In attesa di saldo."*

---

## 📈 Fase 3: Business Intelligence Temporale
Potenziare l'Agente SQL per analisi storiche.

### 3.1 Time-Series SQL
- Implementare query con Window Functions (`LAG`, `LEAD`) per calcolare variazioni percentuali.
- Es: *"Confronta le spese di Gennaio 2026 con Gennaio 2025"*.

### 3.2 Visualizzazione Grafica
- Il Chatbot deve poter restituire non solo testo/tabelle, ma **Grafici**.
- Integrazione Frontend con librerie grafiche (es. Recharts) pilotate dai dati JSON restituiti dall'agente.

---

## 🛣️ Roadmap di Implementazione

| Fase | Attività | Stima | Impatto |
| :--- | :--- | :--- | :--- |
| **1. Lines** | Schema DB `document_lines` + Prompt Extraction Update | 2 Settimane | **Alto** (Abilita tutto il resto) |
| **2. UI** | Interfaccia Validazione Righe (Tabella modificabile) | 2 Settimane | **Medio** (Qualità dato) |
| **3. Logic** | Algoritmo Matching PO-DDT-Fattura | 3 Settimane | **Altissimo** (Valore Enterprise) |
| **4. BI+** | Supporto Query Temporali e Grafici | 2 Settimane | **Alto** (Insight Direzionali) |

## 🏁 Prossimi Passi Consigliati
Suggerisco di iniziare dalla **Fase 1 (Line Items)**. Senza i dettagli delle righe dei documenti, la riconciliazione "vera" è impossibile. Vogliamo procedere in questa direzione?
