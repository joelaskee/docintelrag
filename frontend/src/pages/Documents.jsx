import React from 'react';
import DocumentList from '../components/DocumentList';
import './Documents.css';

export default function Documents() {
    return (
        <div className="documents-page animate-fade-in">
            <header className="page-header">
                <h1>Documenti</h1>
                <p>Gestisci e revisiona i documenti caricati</p>
            </header>

            <DocumentList />
        </div>
    );
}
