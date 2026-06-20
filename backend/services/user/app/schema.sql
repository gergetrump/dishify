CREATE TABLE IF NOT EXISTS user_preferences (
	user_id UUID PRIMARY KEY,
	exclusion_restrictions JSONB NOT NULL DEFAULT '[]',
	updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
