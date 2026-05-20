CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS thoughts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    embedding vector(768),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    category TEXT,
    project TEXT,
    source TEXT,
    importance TEXT
);

CREATE INDEX IF NOT EXISTS idx_thoughts_embedding
    ON thoughts USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_thoughts_category ON thoughts(category);
CREATE INDEX IF NOT EXISTS idx_thoughts_project ON thoughts(project);
CREATE INDEX IF NOT EXISTS idx_thoughts_importance ON thoughts(importance);
CREATE INDEX IF NOT EXISTS idx_thoughts_created_at ON thoughts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_thoughts_metadata ON thoughts USING gin (metadata);

CREATE TABLE IF NOT EXISTS brain_instructions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scope TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    cadence TEXT NOT NULL,
    effective_on DATE,
    project TEXT,
    tool TEXT,
    source TEXT,
    importance TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_brain_instructions_lookup
    ON brain_instructions(scope, cadence, project, tool, effective_on DESC, updated_at DESC);

CREATE OR REPLACE FUNCTION match_thoughts(
    query_embedding vector(768),
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 10,
    filter jsonb DEFAULT '{}'::jsonb
) RETURNS TABLE(
    id uuid,
    content text,
    metadata jsonb,
    category text,
    project text,
    source text,
    importance text,
    similarity float,
    created_at timestamptz
) AS $$
    SELECT
        thoughts.id,
        thoughts.content,
        thoughts.metadata,
        thoughts.category,
        thoughts.project,
        thoughts.source,
        thoughts.importance,
        (1 - (thoughts.embedding <=> query_embedding))::float AS similarity,
        thoughts.created_at
    FROM thoughts
    WHERE (1 - (thoughts.embedding <=> query_embedding)) > match_threshold
    ORDER BY thoughts.embedding <=> query_embedding
    LIMIT match_count;
$$ LANGUAGE sql;
