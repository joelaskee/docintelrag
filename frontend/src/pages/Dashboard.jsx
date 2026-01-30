import { useQuery } from '@tanstack/react-query'
import { dashboardApi } from '../services/api'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { FileText, CheckCircle, AlertTriangle, Clock, Download } from 'lucide-react'
import './Dashboard.css'

const COLORS = ['#6366f1', '#8b5cf6', '#22c55e', '#f59e0b']

export default function Dashboard() {
    const { data, isLoading } = useQuery({
        queryKey: ['dashboard'],
        queryFn: () => dashboardApi.get(30).then(r => r.data),
    })

    const handleExport = async (format) => {
        try {
            const response = await dashboardApi.export(format)
            const blob = new Blob([response.data])
            const url = window.URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = `documents.${format}`
            a.click()
            window.URL.revokeObjectURL(url)
        } catch (error) {
            console.error('Export failed:', error)
        }
    }

    if (isLoading) {
        return (
            <div className="loading-state">
                <div className="spinner-lg"></div>
                <p>Caricamento dashboard...</p>
            </div>
        )
    }

    const kpiIcons = {
        'Total Documents': FileText,
        'Documents (30d)': Clock,
        'Validated': CheckCircle,
        'Failed': AlertTriangle,
    }

    return (
        <div className="dashboard-page animate-fade-in">
            <header className="page-header flex justify-between items-center">
                <div>
                    <h1>Dashboard</h1>
                    <p>Panoramica e statistiche sui documenti</p>
                </div>
                <div className="export-buttons">
                    <button className="btn btn-secondary" onClick={() => handleExport('csv')}>
                        <Download size={16} />
                        Esporta CSV
                    </button>
                </div>
            </header>

            {/* KPI Cards */}
            <div className="kpi-grid">
                {data?.kpis?.map((kpi, i) => {
                    const Icon = kpiIcons[kpi.name] || FileText
                    return (
                        <div key={i} className="kpi-card card">
                            <div className="kpi-icon">
                                <Icon size={24} />
                            </div>
                            <div className="kpi-content">
                                <div className="kpi-value">{kpi.value.toLocaleString()}</div>
                                <div className="kpi-label">{kpi.name}</div>
                            </div>
                        </div>
                    )
                })}
            </div>

            {/* Charts */}
            <div className="charts-grid">
                <div className="chart-card card">
                    <h3>Documenti per Tipo</h3>
                    <div className="chart-container">
                        <ResponsiveContainer width="100%" height={250}>
                            <PieChart>
                                <Pie
                                    data={data?.by_type || []}
                                    dataKey="count"
                                    nameKey="doc_type"
                                    cx="50%"
                                    cy="50%"
                                    outerRadius={80}
                                    label={({ doc_type, count }) => `${doc_type}: ${count}`}
                                >
                                    {data?.by_type?.map((_, i) => (
                                        <Cell key={i} fill={COLORS[i % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                <div className="chart-card card">
                    <h3>Documenti per Stato</h3>
                    <div className="chart-container">
                        <ResponsiveContainer width="100%" height={250}>
                            <BarChart data={data?.by_status || []}>
                                <XAxis dataKey="status" tick={{ fill: '#a1a1a6', fontSize: 12 }} />
                                <YAxis tick={{ fill: '#a1a1a6', fontSize: 12 }} />
                                <Tooltip
                                    contentStyle={{
                                        background: '#1a1a1f',
                                        border: '1px solid rgba(255,255,255,0.1)',
                                        borderRadius: 8,
                                    }}
                                />
                                <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>

            {/* Recent Documents */}
            <div className="recent-card card">
                <h3>Documenti Recenti</h3>
                <div className="recent-list">
                    {data?.recent_documents?.map((doc) => (
                        <a key={doc.id} href={`/documents/${doc.id}`} className="recent-item">
                            <FileText size={16} />
                            <span className="recent-filename">{doc.filename}</span>
                            <span className={`badge badge-${doc.status === 'validated' ? 'success' : doc.status === 'failed' ? 'error' : 'info'}`}>
                                {doc.status}
                            </span>
                            <span className="recent-date">
                                {new Date(doc.created_at).toLocaleDateString('it-IT')}
                            </span>
                        </a>
                    ))}
                </div>
            </div>
        </div>
    )
}
