-- Download history persistence: stores completed/errored task records
-- independently from the aria2 session file (which only keeps active tasks).
CREATE TABLE IF NOT EXISTS download_history (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  gid           TEXT    NOT NULL UNIQUE,
  name          TEXT    NOT NULL,
  uri           TEXT,
  dir           TEXT,
  total_length  INTEGER DEFAULT 0,
  status        TEXT    NOT NULL,
  task_type     TEXT    DEFAULT 'uri',
  created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
  completed_at  DATETIME,
  meta          TEXT
);

CREATE INDEX IF NOT EXISTS idx_dh_status    ON download_history(status);
CREATE INDEX IF NOT EXISTS idx_dh_completed ON download_history(completed_at);
