import React, { useState, useCallback } from 'react';
import { Upload, X, FileText, AlertCircle, CheckCircle } from 'lucide-react';
import { ingestionApi } from '../services/api';

const FileUpload = () => {
    const [dragActive, setDragActive] = useState(false);
    const [files, setFiles] = useState([]);
    const [uploading, setUploading] = useState(false);
    const [uploadStatus, setUploadStatus] = useState(null); // { type: 'success' | 'error', message: '' }

    const handleDrag = useCallback((e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === "dragenter" || e.type === "dragover") {
            setDragActive(true);
        } else if (e.type === "dragleave") {
            setDragActive(false);
        }
    }, []);

    const handleDrop = useCallback((e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            setFiles(Array.from(e.dataTransfer.files));
            setUploadStatus(null);
        }
    }, []);

    const handleChange = useCallback((e) => {
        e.preventDefault();
        if (e.target.files && e.target.files[0]) {
            setFiles(Array.from(e.target.files));
            setUploadStatus(null);
        }
    }, []);

    const removeFile = (index) => {
        const newFiles = [...files];
        newFiles.splice(index, 1);
        setFiles(newFiles);
    };

    const handleUpload = async () => {
        if (files.length === 0) return;

        setUploading(true);
        setUploadStatus(null);

        try {
            // Upload files one by one (or batch if API supports it, but loop is safer for MVP)
            for (const file of files) {
                const formData = new FormData();
                formData.append('files', file);
                // Note: Backend expects 'files' as a list, but we can send one by one or all. 
                // Let's check backend ingestion_router. Assuming it handles List[UploadFile].

                await ingestionApi.upload(formData);
            }
            setUploadStatus({ type: 'success', message: 'Documents uploaded successfully!' });
            setFiles([]);
        } catch (error) {
            console.error('Upload failed:', error);
            setUploadStatus({ type: 'error', message: 'Failed to upload documents. Please try again.' });
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="w-full max-w-3xl mx-auto p-8 card-glass rounded-xl shadow-lg border border-[var(--color-border)]">
            <h2 className="text-2xl font-bold mb-6 text-[var(--color-text-primary)] flex items-center gap-2">
                <Upload className="w-6 h-6 text-primary-500" />
                Upload Documenti
            </h2>

            <div
                className={`relative flex flex-col items-center justify-center w-full h-80 border-3 border-dashed rounded-2xl cursor-pointer transition-all duration-300 group
          ${dragActive
                        ? 'border-primary-500 bg-primary-500/10 scale-[1.02]'
                        : 'border-[var(--color-border)] hover:border-primary-400 hover:bg-[var(--color-bg-hover)]'}`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
            >
                <input
                    type="file"
                    multiple
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                    onChange={handleChange}
                    accept=".pdf,.jpg,.jpeg,.png"
                />

                <div className="flex flex-col items-center justify-center pt-5 pb-6 text-center p-4">
                    <div className={`p-4 rounded-full mb-4 transition-colors ${dragActive ? 'bg-primary-500/20' : 'bg-[var(--color-bg-tertiary)] group-hover:bg-primary-500/10'}`}>
                        <Upload className={`w-10 h-10 ${dragActive ? 'text-primary-400' : 'text-gray-400 group-hover:text-primary-400'}`} />
                    </div>
                    <p className="mb-2 text-lg text-[var(--color-text-primary)] font-medium">
                        Clicca o trascina i file qui
                    </p>
                    <p className="text-sm text-[var(--color-text-secondary)]">PDF, JPG, PNG, JPEG (MAX. 50MB)</p>
                </div>
            </div>

            {/* File List */}
            {files.length > 0 && (
                <div className="mt-6 space-y-2">
                    <h3 className="text-sm font-medium text-gray-700">Selected Files ({files.length})</h3>
                    <ul className="divide-y divide-gray-100">
                        {files.map((file, index) => (
                            <li key={index} className="flex items-center justify-between py-2 text-sm">
                                <div className="flex items-center">
                                    <FileText className="w-4 h-4 mr-2 text-gray-500" />
                                    <span className="truncate max-w-xs">{file.name}</span>
                                    <span className="ml-2 text-gray-400 text-xs">({(file.size / 1024 / 1024).toFixed(2)} MB)</span>
                                </div>
                                <button
                                    onClick={() => removeFile(index)}
                                    className="p-1 hover:bg-gray-100 rounded-full text-gray-500 hover:text-red-500"
                                    disabled={uploading}
                                >
                                    <X className="w-4 h-4" />
                                </button>
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {/* Status Message */}
            {uploadStatus && (
                <div className={`mt-4 p-3 rounded-md flex items-center text-sm ${uploadStatus.type === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
                    }`}>
                    {uploadStatus.type === 'success' ? (
                        <CheckCircle className="w-5 h-5 mr-2" />
                    ) : (
                        <AlertCircle className="w-5 h-5 mr-2" />
                    )}
                    {uploadStatus.message}
                </div>
            )}

            {/* Upload Button */}
            {files.length > 0 && (
                <div className="mt-6 flex justify-end">
                    <button
                        onClick={handleUpload}
                        disabled={uploading}
                        className={`px-4 py-2 rounded-md text-white font-medium transition-colors
              ${uploading
                                ? 'bg-gray-400 cursor-not-allowed'
                                : 'bg-primary-600 hover:bg-primary-700 shadow-sm'}`}
                    >
                        {uploading ? 'Uploading...' : 'Upload Files'}
                    </button>
                </div>
            )}
        </div>
    );
};

export default FileUpload;
