import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Add a request interceptor to add the auth token if it exists
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

export const documentsApi = {
    list: (params) => api.get('/documents', { params }),
    get: (id) => api.get(`/documents/${id}`),
    update: (id, data) => api.patch(`/documents/${id}`, data),
    delete: (id) => api.delete(`/documents/${id}`),
    getFields: (id) => api.get(`/documents/${id}/fields`),
    getLines: (id) => api.get(`/documents/${id}/lines`),
    updateField: (docId, fieldId, data) => api.patch(`/documents/${docId}/fields/${fieldId}`, data),
    getPdf: (id) => {
        const token = localStorage.getItem('token');
        return `${API_URL}/documents/${id}/pdf?token=${encodeURIComponent(token || '')}`;
    },
    // Rotation endpoints
    getPageCount: (id) => api.get(`/documents/${id}/page-count`),
    getPagePreviewUrl: (id, pageNum) => {
        const token = localStorage.getItem('token');
        return `${API_URL}/documents/${id}/pages/${pageNum}/preview`;
    },
    setPageRotation: (id, pageNum, rotation) =>
        api.patch(`/documents/${id}/pages/${pageNum}/rotation`, null, { params: { rotation } }),
    confirmRotation: (id) => api.post(`/documents/${id}/confirm-rotation`),
    reprocess: (id) => api.post(`/documents/${id}/reprocess`),
    stopProcessing: (id) => api.post(`/documents/${id}/stop-processing`),
};

export const ingestionApi = {
    upload: (formData, onUploadProgress) => api.post('/ingestion/upload', formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
            if (onUploadProgress) {
                const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                onUploadProgress(percentCompleted);
            }
        }
    }),
    folder: (path) => {
        const formData = new FormData();
        formData.append('folder_path', path);
        return api.post('/ingestion/folder', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });
    },
};

export const chatApi = {
    // Send message with session ID
    sendMessage: (message, sessionId) => api.post('/chat', { message, session_id: sessionId }),
    // Get list of previous sessions
    getSessions: () => api.get('/chat/sessions'),
    // Get history of a specific session
    getHistory: (sessionId) => api.get(`/chat/sessions/${sessionId}`),
};

export const dashboardApi = {
    get: (days) => api.get('/dashboard', { params: { days } }),
    export: (format) => api.get('/dashboard/export', { params: { format }, responseType: 'blob' }),
};

export const adminApi = {
    listUsers: () => api.get('/admin/users'),
    createUser: (data) => api.post('/admin/users', data),
    updateUser: (id, data) => api.patch(`/admin/users/${id}`, data),
    deleteUser: (id) => api.delete(`/admin/users/${id}`),
    getAudit: () => api.get('/admin/audit'),
};

export const authApi = {
    login: (credentials) => api.post('/auth/login', credentials),
    me: () => api.get('/auth/me'),
}


export default api;
