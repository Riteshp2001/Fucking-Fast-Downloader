#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
manifest="$root_dir/flatpak/com.ff-downloader.app.yml"
build_dir="$root_dir/flatpak/build"
repo_dir="$root_dir/flatpak/repo"
deb_destination="$root_dir/flatpak/ff-downloader.deb"
dist_dir="$root_dir/dist"

for command in flatpak flatpak-builder pnpm; do
  command -v "$command" >/dev/null || {
    echo "Required command not found: $command" >&2
    exit 1
  }
done

cd "$root_dir"
pnpm install --frozen-lockfile
pnpm tauri build --bundles deb --config src-tauri/tauri.ci.conf.json

deb_file="$(find "$root_dir/src-tauri/target/release/bundle/deb" -maxdepth 1 -type f -name '*.deb' -print -quit)"
[[ -n "$deb_file" ]] || { echo "Tauri did not produce a Debian package." >&2; exit 1; }

cp "$deb_file" "$deb_destination"
flatpak-builder --force-clean --repo="$repo_dir" "$build_dir" "$manifest"
flatpak build-update-repo --generate-static-deltas "$repo_dir"

version="$(sed -n 's/^version = "\([^"]*\)"/\1/p' src-tauri/Cargo.toml | head -n 1)"
[[ -n "$version" ]] || { echo "Could not determine the application version." >&2; exit 1; }
mkdir -p "$dist_dir"
flatpak build-bundle "$repo_dir" "$dist_dir/FF-Downloader-${version}-x86_64.flatpak" \
  com.ff-downloader.app --runtime-repo=https://dl.flathub.org/repo/flathub.flatpakrepo
