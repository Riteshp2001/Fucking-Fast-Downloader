use std::path::Path;

pub(crate) const MAX_LOG_FILE_SIZE: u64 = 50 * 1024 * 1024;
pub(crate) const MAX_LOG_FILES: usize = 1;
pub(crate) const MOTRIX_LOG_FILE: &str = "ff-downloader.log";
pub(crate) const ARIA2_LOG_FILE: &str = "aria2-next.log";

pub(crate) fn is_managed_active_log_file(name: &str) -> bool {
    matches!(name, MOTRIX_LOG_FILE | ARIA2_LOG_FILE)
}

fn has_numeric_suffix(name: &str, prefix: &str) -> bool {
    name.strip_prefix(prefix)
        .is_some_and(|index| !index.is_empty() && index.bytes().all(|byte| byte.is_ascii_digit()))
}

pub(crate) fn is_legacy_log_file(name: &str) -> bool {
    let aria2_native = name
        .strip_prefix("aria2-next.")
        .and_then(|rest| rest.strip_suffix(".log"));

    aria2_native
        .is_some_and(|index| !index.is_empty() && index.bytes().all(|byte| byte.is_ascii_digit()))
        || has_numeric_suffix(name, "aria2-next.log.")
        || has_numeric_suffix(name, "ff-downloader.log.")
}

pub(crate) fn remove_legacy_log_files(log_dir: &Path) -> std::io::Result<()> {
    if !log_dir.exists() {
        return Ok(());
    }

    for entry in std::fs::read_dir(log_dir)?.flatten() {
        let path = entry.path();
        let name = path
            .file_name()
            .and_then(|name| name.to_str())
            .unwrap_or("");
        if path.is_file() && is_legacy_log_file(name) {
            std::fs::remove_file(path)?;
        }
    }

    Ok(())
}
