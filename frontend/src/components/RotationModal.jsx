import { useState, useEffect } from 'react';
import { RotateCcw, RotateCw, ChevronLeft, ChevronRight, Check, X, Loader2 } from 'lucide-react';
import { documentsApi } from '../services/api';
import './RotationModal.css';

export default function RotationModal({ document, onClose, onConfirm }) {
    const [currentPage, setCurrentPage] = useState(1);
    const [pageCount, setPageCount] = useState(1);
    const [rotations, setRotations] = useState({});
    const [loading, setLoading] = useState(true);
    const [confirming, setConfirming] = useState(false);
    const [imageUrl, setImageUrl] = useState('');
    const [imageKey, setImageKey] = useState(0);

    useEffect(() => {
        loadPageCount();
    }, [document.id]);

    useEffect(() => {
        loadPagePreview();
    }, [currentPage, rotations, imageKey]);

    const loadPageCount = async () => {
        try {
            const res = await documentsApi.getPageCount(document.id);
            setPageCount(res.data.page_count);
        } catch (err) {
            console.error('Failed to load page count:', err);
        }
    };

    const loadPagePreview = async () => {
        setLoading(true);
        try {
            // Add rotation as query param to force reload after rotation
            const rotation = rotations[currentPage] || 0;
            const url = documentsApi.getPagePreviewUrl(document.id, currentPage);
            const token = localStorage.getItem('token');
            setImageUrl(`${url}?rotation=${rotation}&t=${imageKey}&token=${token}`);
        } finally {
            setLoading(false);
        }
    };

    const rotate = async (direction) => {
        const current = rotations[currentPage] || 0;
        const newRotation = (current + direction + 360) % 360;

        try {
            await documentsApi.setPageRotation(document.id, currentPage, newRotation);
            setRotations(prev => ({ ...prev, [currentPage]: newRotation }));
            setImageKey(prev => prev + 1); // Force image reload
        } catch (err) {
            console.error('Failed to set rotation:', err);
        }
    };

    const handleConfirm = async () => {
        setConfirming(true);
        try {
            await documentsApi.confirmRotation(document.id);
            onConfirm();
        } catch (err) {
            console.error('Failed to confirm rotation:', err);
            alert('Errore durante la conferma: ' + err.message);
        } finally {
            setConfirming(false);
        }
    };

    return (
        <div className="rotation-modal-overlay" onClick={onClose}>
            <div className="rotation-modal" onClick={e => e.stopPropagation()}>
                <div className="rotation-modal-header">
                    <h2>Rotazione Documento</h2>
                    <p className="subtitle">{document.filename}</p>
                    <button className="close-btn" onClick={onClose}>
                        <X size={20} />
                    </button>
                </div>

                <div className="rotation-modal-content">
                    <div className="preview-container">
                        {loading ? (
                            <div className="loading-indicator">
                                <Loader2 className="spin" size={40} />
                            </div>
                        ) : (
                            <img
                                src={imageUrl}
                                alt={`Pagina ${currentPage}`}
                                className="page-preview"
                                style={{ transform: `rotate(${rotations[currentPage] || 0}deg)` }}
                            />
                        )}
                    </div>

                    <div className="controls">
                        <div className="rotation-buttons">
                            <button onClick={() => rotate(-90)} title="Ruota -90°">
                                <RotateCcw size={24} />
                                <span>-90°</span>
                            </button>
                            <button onClick={() => rotate(90)} title="Ruota +90°">
                                <RotateCw size={24} />
                                <span>+90°</span>
                            </button>
                        </div>

                        <div className="page-navigation">
                            <button
                                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                                disabled={currentPage === 1}
                            >
                                <ChevronLeft size={20} />
                            </button>
                            <span>Pagina {currentPage} di {pageCount}</span>
                            <button
                                onClick={() => setCurrentPage(p => Math.min(pageCount, p + 1))}
                                disabled={currentPage === pageCount}
                            >
                                <ChevronRight size={20} />
                            </button>
                        </div>

                        <div className="rotation-status">
                            {Object.keys(rotations).length > 0 && (
                                <span className="rotation-info">
                                    {Object.keys(rotations).length} pagine ruotate
                                </span>
                            )}
                        </div>
                    </div>
                </div>

                <div className="rotation-modal-footer">
                    <button className="cancel-btn" onClick={onClose}>
                        Annulla
                    </button>
                    <button
                        className="confirm-btn"
                        onClick={handleConfirm}
                        disabled={confirming}
                    >
                        {confirming ? (
                            <><Loader2 className="spin" size={16} /> Elaborazione...</>
                        ) : (
                            <><Check size={16} /> Conferma e Processa</>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
}
