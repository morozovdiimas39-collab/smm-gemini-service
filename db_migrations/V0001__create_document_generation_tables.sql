-- Таблица для задач генерации документов
CREATE TABLE IF NOT EXISTS document_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_type VARCHAR(50) NOT NULL,
    subject TEXT NOT NULL,
    pages INTEGER NOT NULL,
    topics JSONB NOT NULL,
    additional_info TEXT,
    quality_level VARCHAR(20) DEFAULT 'high',
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Таблица для разделов документа
CREATE TABLE IF NOT EXISTS document_sections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES document_jobs(id),
    section_index INTEGER NOT NULL,
    section_title TEXT NOT NULL,
    section_description TEXT,
    content TEXT,
    ai_score INTEGER,
    uniqueness_score INTEGER,
    attempt_num INTEGER DEFAULT 1,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_job_id ON document_sections(job_id);
CREATE INDEX idx_job_status ON document_jobs(status);
CREATE INDEX idx_section_status ON document_sections(job_id, status);