-- Position-stable ordering: records when a task was first added.
-- Once set, added_at never changes — used for all sorting operations.
--
-- Uses the SQLite-recommended table rebuild pattern instead of ALTER TABLE
-- because SQLite does not support ALTER TABLE ADD COLUMN IF NOT EXISTS.
-- Every statement is idempotent: safe to re-run on partially migrated
-- databases, dev environments, or interrupted migrations.

-- 1. Preserve existing data in a temporary staging table.
--    Uses only v1-guaranteed columns (no added_at reference) so this
--    works regardless of whether the source table has the column.
CREATE TABLE IF NOT EXISTS _dh_staging (
  id            INTEGER PRIMARY KEY,
  gid           TEXT    NOT NULL UNIQUE,
  name          TEXT    NOT NULL,
  uri           TEXT,
  dir           TEXT,
  total_length  INTEGER DEFAULT 0,
  status        TEXT    NOT NULL,
  task_type     TEXT    DEFAULT 'uri',
  created_at    DATETIME,
  completed_at  DATETIME,
  meta          TEXT
);

INSERT OR IGNORE INTO _dh_staging
  (id, gid, name, uri, dir, total_length, status, task_type,
   created_at, completed_at, meta)
SELECT
  id, gid, name, uri, dir, total_length, status, task_type,
  created_at, completed_at, meta
FROM download_history;

-- 2. Drop the old table (any schema variant).
DROP TABLE IF EXISTS download_history;

-- 3. Create the canonical v2 table with added_at.
CREATE TABLE download_history (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  gid           TEXT    NOT NULL UNIQUE,
  name          TEXT    NOT NULL,
  uri           TEXT,
  dir           TEXT,
  total_length  INTEGER DEFAULT 0,
  status        TEXT    NOT NULL,
  task_type     TEXT    DEFAULT 'uri',
  added_at      DATETIME,
  created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
  completed_at  DATETIME,
  meta          TEXT
);

-- 4. Restore data from staging. Backfill added_at from created_at.
INSERT OR IGNORE INTO download_history
  (id, gid, name, uri, dir, total_length, status, task_type,
   added_at, created_at, completed_at, meta)
SELECT
  id, gid, name, uri, dir, total_length, status, task_type,
  created_at,
  created_at, completed_at, meta
FROM _dh_staging;

-- 5. Clean up staging table.
DROP TABLE IF EXISTS _dh_staging;

-- 6. Restore AUTOINCREMENT sequence so new rows continue from MAX(id).
INSERT OR REPLACE INTO sqlite_sequence (name, seq)
  SELECT 'download_history', COALESCE(MAX(id), 0) FROM download_history;

-- 7. Create indexes.
CREATE INDEX IF NOT EXISTS idx_dh_status    ON download_history(status);
CREATE INDEX IF NOT EXISTS idx_dh_completed ON download_history(completed_at);
CREATE INDEX IF NOT EXISTS idx_dh_added     ON download_history(added_at);

-- 8. Lightweight birth registry for ALL tasks (including active).
--    Persists added_at across restarts so active tasks retain their
--    original position relative to completed tasks.
CREATE TABLE IF NOT EXISTS task_birth (
  gid       TEXT     PRIMARY KEY,
  added_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
