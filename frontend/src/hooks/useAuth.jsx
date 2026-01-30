import { createContext, useContext, useState, useEffect } from 'react'
import api from '../services/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        const token = localStorage.getItem('token')
        if (token) {
            api.defaults.headers.common['Authorization'] = `Bearer ${token}`
            fetchUser()
        } else {
            setLoading(false)
        }
    }, [])

    async function fetchUser() {
        try {
            const response = await api.get('/auth/me')
            setUser(response.data)
        } catch (error) {
            localStorage.removeItem('token')
            delete api.defaults.headers.common['Authorization']
        } finally {
            setLoading(false)
        }
    }

    async function login(email, password) {
        // Use URLSearchParams for proper x-www-form-urlencoded format 
        // required by OAuth2PasswordRequestForm
        const params = new URLSearchParams()
        params.append('username', email)
        params.append('password', password)

        const response = await api.post('/auth/token', params, {
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        })
        const { access_token } = response.data

        localStorage.setItem('token', access_token)
        api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`

        await fetchUser()
    }

    function logout() {
        localStorage.removeItem('token')
        delete api.defaults.headers.common['Authorization']
        setUser(null)
    }

    return (
        <AuthContext.Provider value={{ user, loading, login, logout }}>
            {children}
        </AuthContext.Provider>
    )
}

export function useAuth() {
    const context = useContext(AuthContext)
    if (!context) {
        throw new Error('useAuth must be used within AuthProvider')
    }
    return context
}
