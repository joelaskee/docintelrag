import { Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Layout from './components/Layout'
import Login from './pages/Login'
import Documents from './pages/Documents'
import DocumentDetail from './pages/DocumentDetail'
import Ingestion from './pages/Ingestion'
import Chat from './pages/Chat'
import Dashboard from './pages/Dashboard'
import Admin from './pages/Admin'
import { AuthProvider, useAuth } from './hooks/useAuth'

function ProtectedRoute({ children, roles = [] }) {
    const { user, loading } = useAuth()

    if (loading) {
        return (
            <div className="flex items-center justify-center" style={{ height: '100vh' }}>
                <div className="animate-spin" style={{
                    width: 40,
                    height: 40,
                    border: '3px solid var(--color-border)',
                    borderTopColor: 'var(--color-accent)',
                    borderRadius: '50%'
                }} />
            </div>
        )
    }

    if (!user) {
        return <Navigate to="/login" replace />
    }

    if (roles.length > 0 && !roles.includes(user.role)) {
        return <Navigate to="/" replace />
    }

    return children
}

function AppRoutes() {
    return (
        <Routes>
            <Route path="/login" element={<Login />} />

            <Route path="/" element={
                <ProtectedRoute>
                    <Layout />
                </ProtectedRoute>
            }>
                <Route index element={<Navigate to="/documents" replace />} />
                <Route path="documents" element={<Documents />} />
                <Route path="documents/:id" element={<DocumentDetail />} />
                <Route path="ingestion" element={
                    <ProtectedRoute roles={['admin', 'operatore']}>
                        <Ingestion />
                    </ProtectedRoute>
                } />
                <Route path="chat" element={<Chat />} />
                <Route path="dashboard" element={<Dashboard />} />
                <Route path="admin" element={
                    <ProtectedRoute roles={['admin']}>
                        <Admin />
                    </ProtectedRoute>
                } />
            </Route>
        </Routes>
    )
}

export default function App() {
    return (
        <AuthProvider>
            <AppRoutes />
        </AuthProvider>
    )
}
