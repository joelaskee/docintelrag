import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { documentsApi } from '../services/api'
import { ArrowLeft, Save, Edit2, Check, X, FileText, AlertTriangle } from 'lucide-react'
import './DocumentDetail.css'

export default function DocumentDetail() {
    const { id } = useParams()
    const navigate = useNavigate()
    const queryClient = useQueryClient()
    const [editingField, setEditingField] = useState(null)
    const [editValue, setEditValue] = useState('')

    const { data: document, isLoading } = useQuery({
        queryKey: ['document', id],
        queryFn: () => documentsApi.get(id).then(r => r.data),
    })

    const { data: fields = [] } = useQuery({
        queryKey: ['document-fields', id],
        queryFn: () => documentsApi.getFields(id).then(r => r.data),
        enabled: !!document,
    })

    const { data: lines = [] } = useQuery({
        queryKey: ['document-lines', id],
        queryFn: () => documentsApi.getLines(id).then(r => r.data),
        enabled: !!document,
    })

    const updateField = useMutation({
        mutationFn: ({ fieldId, data }) => documentsApi.updateField(id, fieldId, data),
        onSuccess: () => {
            queryClient.invalidateQueries(['document-fields', id])
            setEditingField(null)
        },
    })

    function startEdit(field) {
        setEditingField(field.id)
        setEditValue(field.normalized_value || field.raw_value || '')
    }

    function saveEdit(field) {
        updateField.mutate({
            fieldId: field.id,
            data: { normalized_value: editValue }
        })
    }

    function cancelEdit() {
        setEditingField(null)
        setEditValue('')
    }

    if (isLoading) {
        return (
            <div className="loading-state">
                <div className="spinner-lg"></div>
                <p>Caricamento documento...</p>
            </div>
        )
    }

    if (!document) {
        return <div className="error-state">Documento non trovato</div>
    }

    const FIELD_LABELS = {
        partita_iva: 'Partita IVA',
        numero_documento: 'Numero Documento',
        data_documento: 'Data',
        emittente: 'Emittente',
        fornitore: 'Destinatario',
        totale: 'Totale',
        vettore: 'Vettore',
        causale_trasporto: 'Causale',
        scadenza_pagamento: 'Scadenza',
        modalita_pagamento: 'Pagamento',
    }

    return (
        <div className="document-detail animate-fade-in">
            <header className="detail-header">
                <button className="btn btn-ghost" onClick={() => navigate('/documents')}>
                    <ArrowLeft size={20} />
                    Indietro
                </button>
                <h1>{document.filename}</h1>
            </header>

            <div className="detail-layout">
                {/* PDF Viewer */}
                <div className="pdf-panel card">
                    <div className="pdf-header">
                        <FileText size={20} />
                        <span>Anteprima PDF</span>
                        <a
                            href={documentsApi.getPdf(id)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="btn btn-ghost"
                            style={{ marginLeft: 'auto', fontSize: '0.75rem' }}
                        >
                            Apri in nuova scheda ↗
                        </a>
                    </div>
                    <div className="pdf-viewer">
                        <object
                            data={documentsApi.getPdf(id)}
                            type="application/pdf"
                            className="pdf-iframe"
                        >
                            <div style={{
                                display: 'flex',
                                flexDirection: 'column',
                                alignItems: 'center',
                                justifyContent: 'center',
                                height: '100%',
                                color: 'var(--color-text-muted)',
                                padding: 'var(--spacing-xl)'
                            }}>
                                <FileText size={48} style={{ marginBottom: 'var(--spacing-md)', opacity: 0.5 }} />
                                <p>Impossibile visualizzare il PDF nel browser.</p>
                                <a
                                    href={documentsApi.getPdf(id)}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="btn btn-primary"
                                    style={{ marginTop: 'var(--spacing-md)' }}
                                >
                                    Scarica PDF
                                </a>
                            </div>
                        </object>
                    </div>
                </div>

                {/* Details Panel */}
                <div className="details-panel">
                    {/* Warnings */}
                    {document.warnings?.length > 0 && (
                        <div className="warnings-card card">
                            <div className="warning-header">
                                <AlertTriangle size={18} />
                                <span>Avvisi</span>
                            </div>
                            <ul className="warning-list">
                                {document.warnings.map((w, i) => (
                                    <li key={i}>{w}</li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {/* Extracted Fields */}
                    <div className="fields-card card">
                        <h3>Campi Estratti</h3>
                        <div className="fields-list">
                            {fields.map(field => (
                                <div key={field.id} className="field-row">
                                    <div className="field-label">
                                        {FIELD_LABELS[field.field_name] || field.field_name}
                                    </div>

                                    {editingField === field.id ? (
                                        <div className="field-edit">
                                            <input
                                                type="text"
                                                className="input"
                                                value={editValue}
                                                onChange={(e) => setEditValue(e.target.value)}
                                                autoFocus
                                            />
                                            <button
                                                className="btn btn-ghost"
                                                onClick={() => saveEdit(field)}
                                                disabled={updateField.isPending}
                                            >
                                                <Check size={16} />
                                            </button>
                                            <button className="btn btn-ghost" onClick={cancelEdit}>
                                                <X size={16} />
                                            </button>
                                        </div>
                                    ) : (
                                        <div className="field-value-row">
                                            <span className="field-value">
                                                {field.normalized_value || field.raw_value || '-'}
                                            </span>
                                            <span className={`confidence ${field.confidence >= 0.8 ? 'high' : field.confidence >= 0.5 ? 'medium' : 'low'}`}>
                                                {Math.round(field.confidence * 100)}%
                                            </span>
                                            <button className="btn btn-ghost edit-btn" onClick={() => startEdit(field)}>
                                                <Edit2 size={14} />
                                            </button>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Line Items */}
                    {lines.length > 0 && (
                        <div className="lines-card card">
                            <h3>Righe Articolo</h3>
                            <div className="lines-table-wrapper">
                                <table className="lines-table">
                                    <thead>
                                        <tr>
                                            <th>#</th>
                                            <th>Codice</th>
                                            <th>Descrizione</th>
                                            <th>Qtà</th>
                                            <th>UM</th>
                                            <th>Prezzo</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {lines.map(line => (
                                            <tr key={line.id}>
                                                <td>{line.line_number}</td>
                                                <td><code>{line.item_code || '-'}</code></td>
                                                <td>{line.description || '-'}</td>
                                                <td>{line.quantity ?? '-'}</td>
                                                <td>{line.unit || '-'}</td>
                                                <td>{line.unit_price ? `€${line.unit_price.toFixed(2)}` : '-'}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
