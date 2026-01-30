import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import {
    FileText, Upload, MessageSquare, BarChart3,
    Settings, LogOut, Menu, X
} from 'lucide-react'
import { useState } from 'react'
import './Layout.css'

export default function Layout() {
    const { user, logout } = useAuth()
    const navigate = useNavigate()
    const [sidebarOpen, setSidebarOpen] = useState(true)

    const handleLogout = () => {
        logout()
        navigate('/login')
    }

    const navItems = [
        { to: '/documents', icon: FileText, label: 'Documenti' },
        { to: '/ingestion', icon: Upload, label: 'Ingestione', roles: ['admin', 'operatore'] },
        { to: '/chat', icon: MessageSquare, label: 'Chat AI' },
        { to: '/dashboard', icon: BarChart3, label: 'Dashboard' },
        { to: '/admin', icon: Settings, label: 'Admin', roles: ['admin'] },
    ]

    const filteredNav = navItems.filter(
        item => !item.roles || item.roles.includes(user?.role)
    )

    return (
        <div className="layout">
            <aside className={`sidebar ${sidebarOpen ? 'open' : 'closed'}`}>
                <div className="sidebar-header">
                    <div className="logo">
                        <div className="logo-icon">D</div>
                        {sidebarOpen && <span className="logo-text">DocIntelRAG</span>}
                    </div>
                    <button className="btn-ghost toggle-btn" onClick={() => setSidebarOpen(!sidebarOpen)}>
                        {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
                    </button>
                </div>

                <nav className="sidebar-nav">
                    {filteredNav.map(item => (
                        <NavLink
                            key={item.to}
                            to={item.to}
                            className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
                        >
                            <item.icon size={20} />
                            {sidebarOpen && <span>{item.label}</span>}
                        </NavLink>
                    ))}
                </nav>

                <div className="sidebar-footer">
                    <div className="user-info">
                        <div className="user-avatar">
                            {user?.full_name?.[0] || user?.email?.[0] || 'U'}
                        </div>
                        {sidebarOpen && (
                            <div className="user-details">
                                <span className="user-name">{user?.full_name || user?.email}</span>
                                <span className="user-role">{user?.role}</span>
                            </div>
                        )}
                    </div>
                    <button className="btn-ghost logout-btn" onClick={handleLogout} title="Logout">
                        <LogOut size={20} />
                    </button>
                </div>
            </aside>

            <main className="main-content">
                <Outlet />
            </main>
        </div>
    )
}
