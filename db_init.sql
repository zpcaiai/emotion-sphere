BEGIN;

CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    email         VARCHAR(255) UNIQUE,
    nickname      VARCHAR(100) NOT NULL DEFAULT '',
    avatar        VARCHAR(500) DEFAULT '',
    openid        VARCHAR(255) UNIQUE,
    unionid       VARCHAR(255) UNIQUE,
    login_type    VARCHAR(20) NOT NULL DEFAULT 'email',
    password_hash VARCHAR(255) DEFAULT '',
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_lower
    ON users (LOWER(email))
    WHERE email IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_users_openid
    ON users(openid)
    WHERE openid IS NOT NULL;

CREATE TABLE IF NOT EXISTS security_audit (
    id          SERIAL PRIMARY KEY,
    event_type  VARCHAR(50) NOT NULL,
    email       VARCHAR(255),
    ip_address  INET,
    user_agent  TEXT DEFAULT '',
    details     JSONB DEFAULT '{}',
    success     BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_security_audit_email
    ON security_audit(email)
    WHERE email IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_security_audit_created
    ON security_audit(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_security_audit_event_type
    ON security_audit(event_type);

CREATE TABLE IF NOT EXISTS user_tokens (
    token       VARCHAR(255) PRIMARY KEY,
    email       VARCHAR(255) NOT NULL,
    data        JSONB NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at  TIMESTAMP,
    ip_address  INET
);

CREATE INDEX IF NOT EXISTS idx_user_tokens_email
    ON user_tokens(email);

CREATE INDEX IF NOT EXISTS idx_user_tokens_expires
    ON user_tokens(expires_at);

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_users_updated_at ON users;

CREATE TRIGGER trg_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

COMMIT;
