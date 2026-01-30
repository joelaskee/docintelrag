import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { documentsApi } from '../services/api';
import {
    FileText,
    MoreVertical,
    AlertTriangle,
    CheckCircle,
    Clock,
    Loader2,
    Search,
    Filter,
    X,
    Eye,
    Download,
    Trash2
} from 'lucide-react';

const StatusBadge = ({ status }) => {
    const styles = {
        queued: 'badge-info',
        processing: 'badge-info',
        extracted: 'badge-success',
        validated: 'badge-success',
        failed: 'badge-error',
    };

    const icons = {
        queued: <Clock className="w-3 h-3" />,
        processing: <Loader2 className="w-3 h-3 animate-spin" />,
        extracted: <FileText className="w-3 h-3" />,
        validated: <CheckCircle className="w-3 h-3" />,
        failed: <AlertTriangle className="w-3 h-3" />,
    };

    return (
        <span className={`badge ${styles[status] || 'badge-info'}`}>
            {icons[status]}
            <span style={{ marginLeft: 4 }}>{status}</span>
        </span>
    );
};

const DocumentList = () => {
    const [documents, setDocuments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [showSearch, setShowSearch] = useState(false);
    const [filterType, setFilterType] = useState('');
    const [showFilter, setShowFilter] = useState(false);
    const [activeMenu, setActiveMenu] = useState(null);

    const fetchDocuments = async () => {
        try {
            setLoading(true);
            const response = await documentsApi.list({ limit: 50 });
            setDocuments(response.data);
            setError(null);
        } catch (err) {
            console.error('Error fetching documents:', err);
            setError('Failed to load documents. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchDocuments();
        const interval = setInterval(fetchDocuments, 15000);
        return () => clearInterval(interval);
    }, []);

    const filteredDocs = documents.filter(doc => {
        const matchesSearch = !searchTerm ||
            doc.filename.toLowerCase().includes(searchTerm.toLowerCase()) ||
            (doc.doc_number && doc.doc_number.toLowerCase().includes(searchTerm.toLowerCase()));
        const matchesType = !filterType || doc.doc_type === filterType;
        return matchesSearch && matchesType;
    });

    const docTypes = [...new Set(documents.map(d => d.doc_type).filter(Boolean))];

    if (loading && documents.length === 0) {
        return (
            <div className="loading-state">
                <div className="spinner-lg"></div>
                <p>Caricamento documenti...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="card" style={{ background: 'var(--color-error)', color: 'white', padding: 'var(--spacing-lg)' }}>
                <div className="flex items-center gap-md">
                    <AlertTriangle size={20} />
                    <span>{error}</span>
                </div>
            </div>
        );
    }

    return (
        <div className="card">
            {/* Header */}
            <div className="flex justify-between items-center" style={{ marginBottom: 'var(--spacing-lg)' }}>
                <div className="flex items-center gap-sm">
                    <h3 style={{ margin: 0 }}>Documents</h3>
                    <span className="badge badge-info">{filteredDocs.length}</span>
                </div>
                <div className="flex gap-sm">
                    <button
                        className={`btn btn-ghost ${showSearch ? 'active' : ''}`}
                        onClick={() => { setShowSearch(!showSearch); setShowFilter(false); }}
                        title="Cerca"
                    >
                        <Search size={18} />
                    </button>
                    <button
                        className={`btn btn-ghost ${showFilter ? 'active' : ''}`}
                        onClick={() => { setShowFilter(!showFilter); setShowSearch(false); }}
                        title="Filtra"
                    >
                        <Filter size={18} />
                    </button>
                </div>
            </div>

            {/* Search Bar */}
            {showSearch && (
                <div style={{ marginBottom: 'var(--spacing-md)' }}>
                    <div style={{ position: 'relative' }}>
                        <Search size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--color-text-muted)' }} />
                        <input
                            type="text"
                            className="input"
                            placeholder="Cerca per nome file o numero documento..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            style={{ paddingLeft: 40 }}
                            autoFocus
                        />
                        {searchTerm && (
                            <button
                                onClick={() => setSearchTerm('')}
                                style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-muted)' }}
                            >
                                <X size={16} />
                            </button>
                        )}
                    </div>
                </div>
            )}

            {/* Filter Bar */}
            {showFilter && (
                <div style={{ marginBottom: 'var(--spacing-md)' }} className="flex gap-sm flex-wrap">
                    <button
                        className={`btn ${!filterType ? 'btn-primary' : 'btn-secondary'}`}
                        onClick={() => setFilterType('')}
                    >
                        Tutti
                    </button>
                    {docTypes.map(type => (
                        <button
                            key={type}
                            className={`btn ${filterType === type ? 'btn-primary' : 'btn-secondary'}`}
                            onClick={() => setFilterType(type)}
                        >
                            {type.toUpperCase()}
                        </button>
                    ))}
                </div>
            )}

            {/* Documents Table */}
            <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                        <tr style={{ borderBottom: '1px solid var(--color-border)' }}>
                            <th style={{ padding: 'var(--spacing-sm) var(--spacing-md)', textAlign: 'left', color: 'var(--color-text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                Nome Documento
                            </th>
                            <th style={{ padding: 'var(--spacing-sm) var(--spacing-md)', textAlign: 'left', color: 'var(--color-text-muted)', fontSize: '0.75rem', textTransform: 'uppercase' }}>
                                Stato
                            </th>
                            <th style={{ padding: 'var(--spacing-sm) var(--spacing-md)', textAlign: 'left', color: 'var(--color-text-muted)', fontSize: '0.75rem', textTransform: 'uppercase' }}>
                                Tipo
                            </th>
                            <th style={{ padding: 'var(--spacing-sm) var(--spacing-md)', textAlign: 'left', color: 'var(--color-text-muted)', fontSize: '0.75rem', textTransform: 'uppercase' }}>
                                Data Upload
                            </th>
                            <th style={{ padding: 'var(--spacing-sm) var(--spacing-md)', textAlign: 'right', color: 'var(--color-text-muted)', fontSize: '0.75rem', textTransform: 'uppercase' }}>
                                Azioni
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        {filteredDocs.length === 0 ? (
                            <tr>
                                <td colSpan="5" style={{ padding: 'var(--spacing-2xl)', textAlign: 'center', color: 'var(--color-text-muted)' }}>
                                    <FileText size={48} style={{ opacity: 0.3, marginBottom: 'var(--spacing-md)' }} />
                                    <p>Nessun documento trovato</p>
                                </td>
                            </tr>
                        ) : (
                            filteredDocs.map((doc) => (
                                <tr
                                    key={doc.id}
                                    style={{
                                        borderBottom: '1px solid var(--color-border)',
                                        transition: 'background var(--transition-fast)'
                                    }}
                                    onMouseEnter={(e) => e.currentTarget.style.background = 'var(--color-bg-tertiary)'}
                                    onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                                >
                                    <td style={{ padding: 'var(--spacing-md)' }}>
                                        <div className="flex items-center gap-md">
                                            <div style={{
                                                width: 36,
                                                height: 36,
                                                background: 'var(--color-accent-muted)',
                                                borderRadius: 'var(--radius-md)',
                                                display: 'flex',
                                                alignItems: 'center',
                                                justifyContent: 'center',
                                                color: 'var(--color-accent)'
                                            }}>
                                                <FileText size={18} />
                                            </div>
                                            <div>
                                                <Link
                                                    to={`/documents/${doc.id}`}
                                                    style={{
                                                        color: 'var(--color-text-primary)',
                                                        fontWeight: 500,
                                                        textDecoration: 'none'
                                                    }}
                                                >
                                                    {doc.filename}
                                                </Link>
                                                {doc.doc_number && /\d/.test(doc.doc_number) && doc.doc_number.length > 1 && (
                                                    <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                                                        N° {doc.doc_number}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </td>
                                    <td style={{ padding: 'var(--spacing-md)' }}>
                                        <StatusBadge status={doc.status} />
                                    </td>
                                    <td style={{ padding: 'var(--spacing-md)' }}>
                                        {doc.doc_type ? (
                                            (() => {
                                                const typeColors = {
                                                    fattura: 'rgba(59, 130, 246, 0.15)', // Blue
                                                    po: 'rgba(16, 185, 129, 0.15)',      // Green
                                                    ddt: 'rgba(245, 158, 11, 0.15)',     // Orange
                                                    preventivo: 'rgba(139, 92, 246, 0.15)', // Purple
                                                    altro: 'var(--color-bg-tertiary)'
                                                };
                                                const typeTextColors = {
                                                    fattura: '#60a5fa',
                                                    po: '#34d399',
                                                    ddt: '#fbbf24',
                                                    preventivo: '#a78bfa',
                                                    altro: 'var(--color-text-secondary)'
                                                };
                                                return (
                                                    <span style={{
                                                        background: typeColors[doc.doc_type.toLowerCase()] || typeColors.altro,
                                                        padding: '4px 8px',
                                                        borderRadius: 'var(--radius-sm)',
                                                        fontSize: '0.75rem',
                                                        fontWeight: 600,
                                                        textTransform: 'uppercase',
                                                        color: typeTextColors[doc.doc_type.toLowerCase()] || typeTextColors.altro,
                                                        border: `1px solid ${typeColors[doc.doc_type.toLowerCase()] || typeColors.altro}`
                                                    }}>
                                                        {doc.doc_type}
                                                        {doc.doc_type_confidence && (
                                                            <span style={{ opacity: 0.7, marginLeft: 4 }}>
                                                                ({Math.round(doc.doc_type_confidence * 100)}%)
                                                            </span>
                                                        )}
                                                    </span>
                                                );
                                            })()
                                        ) : (
                                            <span style={{ color: 'var(--color-text-muted)', fontStyle: 'italic' }}>-</span>
                                        )}
                                    </td>
                                    <td style={{ padding: 'var(--spacing-md)', color: 'var(--color-text-secondary)', fontSize: '0.875rem' }}>
                                        {new Date(doc.created_at).toLocaleDateString('it-IT')}
                                        <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                                            {new Date(doc.created_at).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })}
                                        </div>
                                    </td>
                                    <td style={{ padding: 'var(--spacing-md)', textAlign: 'right', position: 'relative' }}>
                                        <button
                                            className="btn btn-ghost"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                setActiveMenu(activeMenu === doc.id ? null : doc.id);
                                            }}
                                        >
                                            <MoreVertical size={18} />
                                        </button>

                                        {activeMenu === doc.id && (
                                            <div
                                                style={{
                                                    position: 'absolute',
                                                    right: 'var(--spacing-md)',
                                                    top: '100%',
                                                    background: 'var(--color-bg-secondary)',
                                                    border: '1px solid var(--color-border)',
                                                    borderRadius: 'var(--radius-md)',
                                                    boxShadow: 'var(--shadow-lg)',
                                                    zIndex: 10,
                                                    minWidth: 160
                                                }}
                                                onClick={() => setActiveMenu(null)}
                                            >
                                                <Link
                                                    to={`/documents/${doc.id}`}
                                                    style={{
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        gap: 'var(--spacing-sm)',
                                                        padding: 'var(--spacing-sm) var(--spacing-md)',
                                                        color: 'var(--color-text-primary)',
                                                        textDecoration: 'none'
                                                    }}
                                                >
                                                    <Eye size={16} />
                                                    Visualizza
                                                </Link>
                                                <a
                                                    href={documentsApi.getPdf(doc.id)}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    style={{
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        gap: 'var(--spacing-sm)',
                                                        padding: 'var(--spacing-sm) var(--spacing-md)',
                                                        color: 'var(--color-text-primary)',
                                                        textDecoration: 'none'
                                                    }}
                                                >
                                                    <Download size={16} />
                                                    Scarica PDF
                                                </a>
                                            </div>
                                        )}
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default DocumentList;
