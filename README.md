<div align="center">
  <h1>⚡ FF Downloader</h1>

  <p><b>A modern, cross-platform download manager built with Tauri v2, Next.js & Rust</b></p>

  <p>
    Powered by a custom Aria2 Next engine supporting HTTP(S), BitTorrent, Metalink & more.
  </p>

  <br>

  <!-- GitHub Stats Row -->
  <a href="https://github.com/Riteshp2001/Fucking-Fast-Downloader/stargazers">
    <img src="https://img.shields.io/github/stars/Riteshp2001/Fucking-Fast-Downloader?style=for-the-badge&logo=github&logoColor=white&labelColor=1a1a2e&color=ffd700" alt="Stars">
  </a>
  <a href="https://github.com/Riteshp2001/Fucking-Fast-Downloader/forks">
    <img src="https://img.shields.io/github/forks/Riteshp2001/Fucking-Fast-Downloader?style=for-the-badge&logo=github&logoColor=white&labelColor=1a1a2e&color=58a6ff" alt="Forks">
  </a>
  <a href="https://github.com/Riteshp2001/Fucking-Fast-Downloader/watchers">
    <img src="https://img.shields.io/github/watchers/Riteshp2001/Fucking-Fast-Downloader?style=for-the-badge&logo=github&logoColor=white&labelColor=1a1a2e&color=2ea043" alt="Watchers">
  </a>
  <a href="https://github.com/Riteshp2001/Fucking-Fast-Downloader/releases">
    <img src="https://img.shields.io/github/downloads/Riteshp2001/Fucking-Fast-Downloader/total?style=for-the-badge&logo=cloudsmith&logoColor=white&labelColor=1a1a2e&color=7c3aed" alt="Total Downloads">
  </a>
  <a href="https://github.com/Riteshp2001/Fucking-Fast-Downloader/releases/latest">
    <img src="https://img.shields.io/github/v/release/Riteshp2001/Fucking-Fast-Downloader?style=for-the-badge&logo=git&logoColor=white&labelColor=1a1a2e&color=f97316" alt="Latest Release">
  </a>
  <a href="https://github.com/Riteshp2001/Fucking-Fast-Downloader/issues">
    <img src="https://img.shields.io/github/issues/Riteshp2001/Fucking-Fast-Downloader?style=for-the-badge&logo=github&logoColor=white&labelColor=1a1a2e&color=ef4444" alt="Open Issues">
  </a>

  <br>

  <!-- Tech Stack Row -->
  <img src="https://img.shields.io/badge/Rust-1.85%2B-orange?style=for-the-badge&logo=rust&logoColor=white&labelColor=1a1a2e" alt="Rust">
  <img src="https://img.shields.io/badge/Tauri-2-purple?style=for-the-badge&logo=tauri&logoColor=white&labelColor=1a1a2e" alt="Tauri">
  <img src="https://img.shields.io/badge/Next.js-16-black?style=for-the-badge&logo=next.js&logoColor=white&labelColor=1a1a2e" alt="Next.js">
  <img src="https://img.shields.io/badge/TypeScript-5-blue?style=for-the-badge&logo=typescript&logoColor=white&labelColor=1a1a2e" alt="TypeScript">
  <img src="https://img.shields.io/badge/MIT-License-yellow?style=for-the-badge&logo=open-source-initiative&logoColor=white&labelColor=1a1a2e" alt="License">

  <br>
  <br>

  <!-- Star History Graph -->
  <a href="https://star-history.com/#Riteshp2001/Fucking-Fast-Downloader&Date">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=Riteshp2001/Fucking-Fast-Downloader&type=Date&theme=dark">
      <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=Riteshp2001/Fucking-Fast-Downloader&type=Date">
      <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=Riteshp2001/Fucking-Fast-Downloader&type=Date" width="700">
    </picture>
  </a>

  <br>
  <br>

  <a href="#features">Features</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#build">Build</a> •
  <a href="#tech-stack">Tech Stack</a> •
  <a href="#download">Download</a> •
  <a href="#support">Support</a>

  <br>
  <br>

  [![Buy Me a Coffee](https://img.shields.io/badge/Buy_Me_A_Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/riteshp2001/e/367661)
</div>

<br>

---

## 🚀 Features

<table>
<tr>
<td width="50%">

### 📥 Multi-Protocol
HTTP(S), BitTorrent, Metalink, Magnet links, and ED2K — one app handles them all.

### ⏯️ Pause / Resume
Full session persistence across restarts. Pick up exactly where you left off.

### 📊 Real-Time Speed Tracking
Per-download and aggregate throughput monitoring with live charts.

### 🌐 BitTorrent
DHT, PEX, Magnet URI, trackerless torrents, and peer blocklist support.

</td>
<td width="50%">

### ⚡ UPnP Port Mapping
Automatic NAT traversal for faster P2P connections.

### 🌍 GeoIP
Peer location lookup via bundled GeoIP database.

### 🌙 Dark Theme
Modern frameless dark UI with Material Web Components.

### 🖥️ System Tray
Minimise to tray with background download support.

### 🔋 Power Management
Prevent system sleep during active downloads.

### 🌐 Localised
27 languages with i18n throughout the UI and installer.

### 🔄 Auto Updates
Built-in updater checking GitHub releases — always stay up-to-date.

</td>
</tr>
</table>

---

## 📦 Download

Get the latest build from the [Releases page](https://github.com/Riteshp2001/Fucking-Fast-Downloader/releases).

| Platform | Format |
|----------|--------|
| Windows  | `.exe` (NSIS installer) |
| macOS    | `.dmg` (Apple Silicon + Intel) |
| Linux    | `.deb` / `.rpm` / `.AppImage` |

---

## 🛠️ Quick Start

```bash
# Clone the repo
git clone https://github.com/Riteshp2001/Fucking-Fast-Downloader.git
cd Fucking-Fast-Downloader

# Install frontend dependencies
pnpm install

# Start development (Next.js + Tauri)
pnpm tauri:dev
```

### Prerequisites

- [Node.js](https://nodejs.org/) >= 20
- [pnpm](https://pnpm.io/) >= 10
- [Rust](https://www.rust-lang.org/) >= 1.85
- Platform build tools — see [Tauri prerequisites](https://v2.tauri.app/start/prerequisites/)

---

## 🏗️ Build

```bash
pnpm tauri:build
```

Artifacts land in `src-tauri/target/release/bundle/`.

---

## 🧩 Tech Stack

| Layer | Technology |
|-------|-----------|
| **Desktop Shell** | [Tauri v2](https://v2.tauri.app) |
| **Frontend** | [Next.js 16](https://nextjs.org) + [React 19](https://react.dev) + [TypeScript 5](https://www.typescriptlang.org) |
| **Backend** | [Rust](https://www.rust-lang.org) with Tokio async runtime |
| **Download Engine** | Aria2 Next (custom C++ sidecar) |
| **UI Components** | [Material Web](https://material-web.dev) + [Tailwind CSS 4](https://tailwindcss.com) |
| **State Management** | [Zustand](https://github.com/pmndrs/zustand) + [TanStack Query](https://tanstack.com/query) |
| **Database** | SQLite via `tauri-plugin-sql` |
| **Icons** | [Solar Icons](https://solar-icons.com) |

---

## 📁 Project Structure

```
├── src/                     # Next.js frontend
│   ├── app/                 # App router pages
│   └── components/          # React components
├── src-tauri/               # Rust / Tauri backend
│   ├── src/
│   │   ├── aria2/           # Aria2 JSON-RPC client
│   │   ├── commands/        # Tauri IPC commands (22 modules)
│   │   ├── engine/          # Download engine lifecycle
│   │   └── services/        # Background services (15 modules)
│   ├── binaries/            # Prebuilt engine sidecars
│   ├── capabilities/        # Tauri v2 permissions
│   └── migrations/          # SQLite schema migrations
└── package.json
```

---

## 📊 GitHub Stats

<div align="center">
  <img src="https://github-readme-stats.vercel.app/api/pin/?username=Riteshp2001&repo=Fucking-Fast-Downloader&theme=radical&hide_border=true" alt="Repo Card">
  <br><br>
  <img src="https://github-readme-stats.vercel.app/api/top-langs/?username=Riteshp2001&repo=Fucking-Fast-Downloader&layout=compact&theme=radical&hide_border=true" alt="Languages">
</div>

---

## ☕ Support

If you find this project useful, consider supporting development:

[![Buy Me a Coffee](https://img.shields.io/badge/Buy_Me_A_Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/riteshp2001/e/367661)

---

## 📄 License

MIT — see [LICENSE](./LICENSE).

---

<div align="center">
  <sub>Built with ❤️ by <a href="https://github.com/Riteshp2001">Ritesh Pandit</a></sub>
</div>
