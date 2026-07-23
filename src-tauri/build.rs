fn main() {
    tauri_build::build();

    // On macOS, clear quarantine flags from sidecar binaries so they can execute.
    // This runs AFTER tauri_build::build() which copies sidecars into target/.
    #[cfg(target_os = "macos")]
    {
        use std::process::Command;
        // Clear source binaries
        let _ = Command::new("xattr").args(["-cr", "binaries/"]).status();
        // Clear copied sidecars in target/debug and target/release.
        let _ = Command::new("sh")
            .args([
                "-c",
                "xattr -cr target/debug/motrix-next-engine* target/release/motrix-next-engine* 2>/dev/null || true",
            ])
            .status();
    }
}
