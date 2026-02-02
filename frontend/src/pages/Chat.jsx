import { useState, useRef, useEffect } from 'react'
import { useMutation } from '@tanstack/react-query'
import { chatApi } from '../services/api'
import { Send, Bot, User, FileText, Loader2 } from 'lucide-react'
import './Chat.css'

export default function Chat() {
    const [message, setMessage] = useState('')
    const [history, setHistory] = useState([])
    const [sessionId, setSessionId] = useState(null)
    const messagesEndRef = useRef(null)

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }

    // Load initial session on mount
    useEffect(() => {
        const loadSession = async () => {
            try {
                const sessionsRes = await chatApi.getSessions()
                if (sessionsRes.data && sessionsRes.data.length > 0) {
                    const lastSession = sessionsRes.data[0]
                    setSessionId(lastSession.id)

                    try {
                        const historyRes = await chatApi.getHistory(lastSession.id)
                        setHistory(historyRes.data)
                    } catch (e) {
                        console.error("Failed to load history:", e)
                    }
                }
            } catch (err) {
                console.error("Failed to load sessions:", err)
            }
        }
        loadSession()
    }, [])

    useEffect(() => {
        scrollToBottom()
    }, [history])

    const sendMessage = useMutation({
        mutationFn: async (msg) => {
            const response = await chatApi.sendMessage(msg, sessionId)
            return response.data
        },
        onSuccess: (data, variables) => {
            // Update session ID if it was a new session
            if (!sessionId && data.session_id) {
                setSessionId(data.session_id)
            }

            setHistory(prev => [
                ...prev,
                { role: 'user', content: variables },
                {
                    role: 'assistant',
                    content: data.message,
                    citations: data.citations,
                    used_reconciliation: data.used_reconciliation
                }
            ])
        },
    })

    const handleSubmit = (e) => {
        e.preventDefault()
        if (message.trim() && !sendMessage.isPending) {
            const msg = message.trim()
            setMessage('')
            sendMessage.mutate(msg)
        }
    }

    return (
        <div className="chat-page animate-fade-in">
            <header className="page-header">
                <h1>Chat AI</h1>
                <p>Interroga i tuoi documenti in linguaggio naturale</p>
            </header>

            <div className="chat-container card">
                <div className="messages-container">
                    {history.length === 0 ? (
                        <div className="empty-chat">
                            <Bot size={48} />
                            <h3>Ciao! Come posso aiutarti?</h3>
                            <p>Puoi chiedermi informazioni sui documenti caricati.</p>
                            <div className="suggestions">
                                <button onClick={() => setMessage("Qual è la spesa totale?")}>
                                    Qual è la spesa totale?
                                </button>
                                <button onClick={() => setMessage("Chi sono i primi 3 fornitori?")}>
                                    Chi sono i primi 3 fornitori?
                                </button>
                                <button onClick={() => setMessage("Cerca l'ultima fattura di A2A")}>
                                    Cerca l'ultima fattura di A2A
                                </button>
                            </div>
                        </div>
                    ) : (
                        <div className="messages">
                            {history.map((msg, i) => (
                                <div key={i} className={`message ${msg.role}`}>
                                    <div className="message-avatar">
                                        {msg.role === 'user' ? <User size={18} /> : <Bot size={18} />}
                                    </div>
                                    <div className="message-content">
                                        <div className="message-text">{msg.content}</div>

                                        {msg.citations?.length > 0 && (
                                            <div className="citations">
                                                <span className="citations-label">Fonti:</span>
                                                {msg.citations.map((c, j) => (
                                                    <a
                                                        key={j}
                                                        href={`/documents/${c.document_id}`}
                                                        className="citation-badge"
                                                    >
                                                        <FileText size={12} />
                                                        {c.filename}
                                                        {c.page && `, p.${c.page}`}
                                                    </a>
                                                ))}
                                            </div>
                                        )}

                                        {msg.used_reconciliation && (
                                            <div className="reconciliation-badge">
                                                🔄 Riconciliazione utilizzata
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ))}

                            {sendMessage.isPending && (
                                <div className="message assistant loading">
                                    <div className="message-avatar">
                                        <Bot size={18} />
                                    </div>
                                    <div className="message-content">
                                        <Loader2 size={18} className="animate-spin" />
                                        <span>Sto elaborando...</span>
                                    </div>
                                </div>
                            )}

                            <div ref={messagesEndRef} />
                        </div>
                    )}
                </div>

                <form className="chat-input-form" onSubmit={handleSubmit}>
                    <input
                        type="text"
                        className="input chat-input"
                        placeholder="Scrivi un messaggio..."
                        value={message}
                        onChange={(e) => setMessage(e.target.value)}
                        disabled={sendMessage.isPending}
                    />
                    <button
                        type="submit"
                        className="btn btn-primary send-btn"
                        disabled={!message.trim() || sendMessage.isPending}
                    >
                        <Send size={18} />
                    </button>
                </form>
            </div>
        </div>
    )
}
