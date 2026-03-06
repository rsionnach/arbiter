-- Arbiter score store schema — this IS the storage contract.
-- All judgment lives in the model, not the schema. No computed "good/bad" columns.

CREATE TABLE IF NOT EXISTS evaluations (
    eval_id TEXT PRIMARY KEY,
    agent_name TEXT NOT NULL,
    task_id TEXT NOT NULL,
    evaluator_model TEXT NOT NULL,
    confidence REAL NOT NULL,
    cost_usd REAL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS dimension_scores (
    eval_id TEXT NOT NULL REFERENCES evaluations(eval_id),
    dimension TEXT NOT NULL,
    score REAL NOT NULL,
    reasoning TEXT,
    PRIMARY KEY (eval_id, dimension)
);

CREATE TABLE IF NOT EXISTS overrides (
    override_id TEXT PRIMARY KEY,
    eval_id TEXT NOT NULL REFERENCES evaluations(eval_id),
    dimension TEXT NOT NULL,
    original_score REAL NOT NULL,
    corrected_score REAL NOT NULL,
    corrector TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_evaluations_agent ON evaluations(agent_name, created_at);
CREATE INDEX IF NOT EXISTS idx_overrides_eval ON overrides(eval_id);
