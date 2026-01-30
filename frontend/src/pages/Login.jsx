import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { Lock, Mail, AlertCircle } from 'lucide-react'
import './Login.css'

export default function Login() {
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)
    const { login } = useAuth()
    const navigate = useNavigate()

    async function handleSubmit(e) {
        e.preventDefault()
        setError('')
        setLoading(true)

        try {
            await login(email, password)
            navigate('/')
        } catch (err) {
            // Handle various error formats from FastAPI
            let errorMessage = 'Credenziali non valide';
            const detail = err.response?.data?.detail;

            if (typeof detail === 'string') {
                errorMessage = detail;
            } else if (Array.isArray(detail) && detail.length > 0) {
                // Validation error array from FastAPI
                errorMessage = detail[0]?.msg || 'Errore di validazione';
            } else if (detail && typeof detail === 'object') {
                errorMessage = detail.msg || detail.message || JSON.stringify(detail);
            }

            setError(errorMessage)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="login-page">
            <div className="login-bg">
                <div className="bg-gradient"></div>
                <div className="bg-grid"></div>
            </div>

            <div className="login-container">
                <div className="login-card card-glass">
                    <div className="login-header">
                        <div className="login-logo">
                            <div className="logo-icon">D</div>
                        </div>
                        <h1>DocIntelRAG</h1>
                        <p>Document Intelligence Platform</p>
                    </div>

                    <form onSubmit={handleSubmit} className="login-form">
                        {error && (
                            <div className="error-alert">
                                <AlertCircle size={18} />
                                <span>{error}</span>
                            </div>
                        )}

                        <div className="form-group">
                            <label htmlFor="email">Username</label>
                            <div className="input-wrapper">
                                <Mail size={18} className="input-icon" />
                                <input
                                    id="email"
                                    type="text"
                                    className="input"
                                    placeholder="admin"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    required
                                />
                            </div>
                        </div>

                        <div className="form-group">
                            <label htmlFor="password">Password</label>
                            <div className="input-wrapper">
                                <Lock size={18} className="input-icon" />
                                <input
                                    id="password"
                                    type="password"
                                    className="input"
                                    placeholder="••••••••"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    required
                                />
                            </div>
                        </div>

                        <button
                            type="submit"
                            className="btn btn-primary login-btn"
                            disabled={loading}
                        >
                            {loading ? (
                                <span className="spinner"></span>
                            ) : (
                                'Accedi'
                            )}
                        </button>
                    </form>
                </div>
            </div>
        </div>
    )
}
