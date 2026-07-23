-- HTTP Basic Auth credentials scoped by normalized URL origin.
CREATE TABLE IF NOT EXISTS http_auth_credentials (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  origin        TEXT     NOT NULL,
  username      TEXT     NOT NULL,
  password      TEXT     NOT NULL,
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_used_at  DATETIME,
  UNIQUE(origin, username)
);

CREATE INDEX IF NOT EXISTS idx_http_auth_credentials_origin
  ON http_auth_credentials(origin);
