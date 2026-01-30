import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { adminApi } from '../services/api'
import { Users, Plus, Edit2, Trash2, X } from 'lucide-react'
import './Admin.css'

export default function Admin() {
    const queryClient = useQueryClient()
    const [showModal, setShowModal] = useState(false)
    const [editingUser, setEditingUser] = useState(null)
    const [formData, setFormData] = useState({
        email: '',
        password: '',
        full_name: '',
        role: 'operatore',
    })

    const { data: users = [], isLoading } = useQuery({
        queryKey: ['users'],
        queryFn: () => adminApi.listUsers().then(r => r.data),
    })

    const { data: audit = [] } = useQuery({
        queryKey: ['audit'],
        queryFn: () => adminApi.getAudit().then(r => r.data),
    })

    const createUser = useMutation({
        mutationFn: (data) => adminApi.createUser(data),
        onSuccess: () => {
            queryClient.invalidateQueries(['users'])
            closeModal()
        },
    })

    const updateUser = useMutation({
        mutationFn: ({ id, data }) => adminApi.updateUser(id, data),
        onSuccess: () => {
            queryClient.invalidateQueries(['users'])
            closeModal()
        },
    })

    const deleteUser = useMutation({
        mutationFn: (id) => adminApi.deleteUser(id),
        onSuccess: () => {
            queryClient.invalidateQueries(['users'])
        },
    })

    function openModal(user = null) {
        if (user) {
            setEditingUser(user)
            setFormData({
                email: user.email,
                password: '',
                full_name: user.full_name || '',
                role: user.role,
            })
        } else {
            setEditingUser(null)
            setFormData({
                email: '',
                password: '',
                full_name: '',
                role: 'operatore',
            })
        }
        setShowModal(true)
    }

    function closeModal() {
        setShowModal(false)
        setEditingUser(null)
    }

    function handleSubmit(e) {
        e.preventDefault()
        if (editingUser) {
            const data = { ...formData }
            if (!data.password) delete data.password
            updateUser.mutate({ id: editingUser.id, data })
        } else {
            createUser.mutate({ ...formData, tenant_id: users[0]?.tenant_id })
        }
    }

    return (
        <div className="admin-page animate-fade-in">
            <header className="page-header">
                <h1>Amministrazione</h1>
                <p>Gestione utenti e configurazioni</p>
            </header>

            {/* Users Section */}
            <div className="admin-section card">
                <div className="section-header">
                    <h3><Users size={20} /> Utenti</h3>
                    <button className="btn btn-primary" onClick={() => openModal()}>
                        <Plus size={16} />
                        Nuovo Utente
                    </button>
                </div>

                {isLoading ? (
                    <div className="loading-state">Caricamento...</div>
                ) : (
                    <table className="users-table">
                        <thead>
                            <tr>
                                <th>Email</th>
                                <th>Nome</th>
                                <th>Ruolo</th>
                                <th>Stato</th>
                                <th>Azioni</th>
                            </tr>
                        </thead>
                        <tbody>
                            {users.map((user) => (
                                <tr key={user.id}>
                                    <td>{user.email}</td>
                                    <td>{user.full_name || '-'}</td>
                                    <td>
                                        <span className={`badge badge-${user.role === 'admin' ? 'error' : user.role === 'operatore' ? 'info' : 'success'}`}>
                                            {user.role}
                                        </span>
                                    </td>
                                    <td>
                                        <span className={`badge badge-${user.is_active === 'Y' ? 'success' : 'error'}`}>
                                            {user.is_active === 'Y' ? 'Attivo' : 'Disattivato'}
                                        </span>
                                    </td>
                                    <td>
                                        <div className="action-buttons">
                                            <button className="btn btn-ghost" onClick={() => openModal(user)}>
                                                <Edit2 size={16} />
                                            </button>
                                            <button
                                                className="btn btn-ghost delete-btn"
                                                onClick={() => deleteUser.mutate(user.id)}
                                            >
                                                <Trash2 size={16} />
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>

            {/* Audit Log */}
            <div className="admin-section card">
                <h3>Audit Log (ultime 100 modifiche)</h3>
                <div className="audit-list">
                    {audit.slice(0, 20).map((entry) => (
                        <div key={entry.id} className="audit-entry">
                            <span className="audit-type">{entry.event_type}</span>
                            <span className="audit-change">
                                {entry.old_value} → {entry.new_value}
                            </span>
                            <span className="audit-date">
                                {new Date(entry.created_at).toLocaleString('it-IT')}
                            </span>
                        </div>
                    ))}
                    {audit.length === 0 && (
                        <p className="empty-text">Nessuna modifica registrata</p>
                    )}
                </div>
            </div>

            {/* User Modal */}
            {showModal && (
                <div className="modal-overlay" onClick={closeModal}>
                    <div className="modal card" onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <h3>{editingUser ? 'Modifica Utente' : 'Nuovo Utente'}</h3>
                            <button className="btn btn-ghost" onClick={closeModal}>
                                <X size={20} />
                            </button>
                        </div>
                        <form onSubmit={handleSubmit} className="modal-form">
                            <div className="form-group">
                                <label>Email</label>
                                <input
                                    type="email"
                                    className="input"
                                    value={formData.email}
                                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                    required
                                />
                            </div>
                            <div className="form-group">
                                <label>Password {editingUser && '(lascia vuoto per non modificare)'}</label>
                                <input
                                    type="password"
                                    className="input"
                                    value={formData.password}
                                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                                    required={!editingUser}
                                />
                            </div>
                            <div className="form-group">
                                <label>Nome Completo</label>
                                <input
                                    type="text"
                                    className="input"
                                    value={formData.full_name}
                                    onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                                />
                            </div>
                            <div className="form-group">
                                <label>Ruolo</label>
                                <select
                                    className="input"
                                    value={formData.role}
                                    onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                                >
                                    <option value="operatore">Operatore</option>
                                    <option value="manager">Manager</option>
                                    <option value="admin">Admin</option>
                                </select>
                            </div>
                            <div className="modal-actions">
                                <button type="button" className="btn btn-secondary" onClick={closeModal}>
                                    Annulla
                                </button>
                                <button type="submit" className="btn btn-primary">
                                    {editingUser ? 'Salva' : 'Crea'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    )
}
