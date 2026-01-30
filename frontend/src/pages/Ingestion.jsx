import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { ingestionApi } from '../services/api';
import FileUpload from '../components/FileUpload';
import { Folder, Upload, CheckCircle, AlertCircle, X } from 'lucide-react';
import './Ingestion.css';

export default function Ingestion() {
    const [mode, setMode] = useState('upload'); // 'upload' or 'folder'
    const [folderPath, setFolderPath] = useState('');
    const [result, setResult] = useState(null);

    const folderMutation = useMutation({
        mutationFn: (path) => ingestionApi.folder(path),
        onSuccess: (response) => {
            setResult({ success: true, data: response.data });
            setFolderPath('');
        },
        onError: (error) => {
            setResult({ success: false, error: error.message || 'Error processing folder' });
        },
    });

    const handleFolderIngest = () => {
        if (folderPath.trim()) {
            folderMutation.mutate(folderPath);
        }
    };

    return (
        <div className="ingestion-page animate-fade-in p-8 min-h-screen">
            <div className="max-w-4xl mx-auto">
                {/* Mode Switcher */}
                <div className="flex justify-center mb-8">
                    <div className="inline-flex bg-[var(--color-bg-tertiary)] p-1.5 rounded-xl border border-[var(--color-border)]">
                        <button
                            className={`px-6 py-2.5 rounded-lg flex items-center gap-2 transition-all duration-200 font-medium ${mode === 'upload' ? 'bg-[var(--color-bg-hover)] text-[var(--color-text-primary)] shadow-sm' : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-hover)]/50'}`}
                            onClick={() => setMode('upload')}
                        >
                            <Upload size={18} />
                            Upload File
                        </button>
                        <button
                            className={`px-6 py-2.5 rounded-lg flex items-center gap-2 transition-all duration-200 font-medium ${mode === 'folder' ? 'bg-[var(--color-bg-hover)] text-[var(--color-text-primary)] shadow-sm' : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-hover)]/50'}`}
                            onClick={() => setMode('folder')}
                        >
                            <Folder size={18} />
                            Cartella Server
                        </button>
                    </div>
                </div>

                {/* Content Area */}
                {mode === 'upload' ? (
                    <div className="upload-section">
                        <FileUpload />
                    </div>
                ) : (
                    <div className="folder-section card-glass p-8 rounded-xl shadow-lg border border-[var(--color-border)] max-w-2xl mx-auto">
                        <h3 className="text-xl font-bold mb-2 text-[var(--color-text-primary)] flex items-center gap-2">
                            <Folder className="w-6 h-6 text-primary-500" />
                            Cartella Server
                        </h3>
                        <p className="text-[var(--color-text-secondary)] mb-6">
                            Inserisci il percorso assoluto di una cartella sul server per importare massivamente i PDF o Immagini.
                        </p>
                        <div className="flex gap-2">
                            <input
                                type="text"
                                className="flex-1 px-4 py-3 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] text-[var(--color-text-primary)] rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 shadow-sm"
                                placeholder="/path/to/documents"
                                value={folderPath}
                                onChange={(e) => setFolderPath(e.target.value)}
                            />
                            <button
                                className="btn btn-primary px-6 py-3 rounded-lg shadow-sm"
                                onClick={handleFolderIngest}
                                disabled={folderMutation.isPending || !folderPath.trim()}
                            >
                                {folderMutation.isPending ? 'Avvia' : 'Avvia'}
                            </button>
                        </div>
                    </div>
                )}

                {/* Result Notification */}
                {result && (
                    <div className={`mt-6 p-4 rounded-xl flex items-start gap-4 mx-auto max-w-2xl shadow-sm border ${result.success ? 'bg-green-900/20 text-green-400 border-green-900/30' : 'bg-red-900/20 text-red-400 border-red-900/30'}`}>
                        {result.success ? <CheckCircle className="flex-shrink-0 w-6 h-6 mt-0.5" /> : <AlertCircle className="flex-shrink-0 w-6 h-6 mt-0.5" />}
                        <div className="flex-1">
                            <h4 className="font-semibold text-lg">{result.success ? 'Operazione Completata' : 'Errore'}</h4>
                            <p className="mt-1 opacity-90 text-sm">
                                {result.success
                                    ? `Creati ${result.data.documents_created?.length || 0} documenti. ${result.data.message || ''}`
                                    : result.error}
                            </p>
                        </div>
                        <button className="text-current opacity-50 hover:opacity-100 transition-opacity" onClick={() => setResult(null)}>
                            <X size={20} />
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}
