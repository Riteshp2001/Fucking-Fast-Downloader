<div align="center">

# FF Downloader

### A fast, modern, cross-platform download manager

Built with **Tauri v2**, **Next.js**, **TypeScript**, and **Rust**.

Powered by a custom **Aria2 Next** engine with support for HTTP(S), BitTorrent, Magnet links, Metalink, ED2K, and more.

<br>

[![Latest Release](https://img.shields.io/github/v/release/Riteshp2001/Fucking-Fast-Downloader?style=flat-square\&logo=github\&color=blue)](https://github.com/Riteshp2001/Fucking-Fast-Downloader/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/Riteshp2001/Fucking-Fast-Downloader/total?style=flat-square\&logo=github)](https://github.com/Riteshp2001/Fucking-Fast-Downloader/releases)
[![Stars](https://img.shields.io/github/stars/Riteshp2001/Fucking-Fast-Downloader?style=flat-square\&logo=github)](https://github.com/Riteshp2001/Fucking-Fast-Downloader/stargazers)
[![Issues](https://img.shields.io/github/issues/Riteshp2001/Fucking-Fast-Downloader?style=flat-square\&logo=github)](https://github.com/Riteshp2001/Fucking-Fast-Downloader/issues)
[![License](https://img.shields.io/github/license/Riteshp2001/Fucking-Fast-Downloader?style=flat-square)](./LICENSE)

<br>

[Download](#download) ·
[Features](#features) ·
[Quick Start](#quick-start) ·
[Build](#build-from-source) ·
[Architecture](#architecture) ·
[Contributing](#contributing)

<br>

[Support the project](https://buymeacoffee.com/riteshp2001/e/367661)

</div>

---

## Overview

FF Downloader is a desktop download manager designed for fast, reliable, and persistent downloads across Windows, macOS, and Linux.

It combines a lightweight Tauri desktop shell with a modern Next.js interface, a Rust backend, and a custom Aria2-based download engine.

The application supports regular file downloads, torrents, magnet links, Metalink files, ED2K links, background downloading, session recovery, real-time speed monitoring, automatic updates, and more.

---

## Features

### Download Management

* HTTP and HTTPS downloads
* BitTorrent downloads
* Magnet URI support
* Metalink support
* ED2K support
* Pause, resume, retry, and cancel operations
* Persistent download sessions
* Automatic recovery after application restart
* Per-download and global speed monitoring
* Real-time download progress updates

### BitTorrent and Peer-to-Peer

* Distributed Hash Table support
* Peer Exchange support
* Trackerless torrent support
* Magnet metadata retrieval
* Peer blocklist support
* Automatic UPnP port mapping
* GeoIP-based peer location lookup

### Desktop Integration

* Windows, macOS, and Linux support
* System tray integration
* Background downloading
* Native desktop notifications
* Power management during active downloads
* Automatic update checks through GitHub Releases
* Frameless desktop interface
* Dark theme

### Internationalisation

* 27 supported languages
* Localised application interface
* Localised installer experience
* Centralised translation management

---

## Download

Download the latest stable version from the GitHub Releases page:

### [Download FF Downloader](https://github.com/Riteshp2001/Fucking-Fast-Downloader/releases/latest)

| Platform | Available Formats                  |
| -------- | ---------------------------------- |
| Windows  | `.exe` NSIS installer              |
| macOS    | `.dmg` for Apple Silicon and Intel |
| Linux    | `.AppImage`, `.deb`, and `.rpm`    |

> Installation packages and supported architectures may vary between releases.

---

## Quick Start

### Prerequisites

Make sure the following tools are installed:

| Requirement | Minimum Version |
| ----------- | --------------: |
| Node.js     |              20 |
| pnpm        |              10 |
| Rust        |            1.85 |

You will also need the platform-specific dependencies listed in the official [Tauri prerequisites documentation](https://v2.tauri.app/start/prerequisites/).

### Clone the Repository

```bash
git clone https://github.com/Riteshp2001/Fucking-Fast-Downloader.git
cd Fucking-Fast-Downloader
```

### Install Dependencies

```bash
pnpm install
```

### Start the Development Application

```bash
pnpm tauri:dev
```

This starts the Next.js frontend and launches the application through Tauri.

---

## Build from Source

Create a production build with:

```bash
pnpm tauri:build
```

Generated installers and application bundles are placed inside:

```text
src-tauri/target/release/bundle/
```

The exact output format depends on the operating system used for the build.

---

## Technology Stack

| Layer             | Technology                                     |
| ----------------- | ---------------------------------------------- |
| Desktop framework | [Tauri v2](https://v2.tauri.app)               |
| Frontend          | [Next.js 16](https://nextjs.org)               |
| UI library        | [React 19](https://react.dev)                  |
| Language          | [TypeScript 5](https://www.typescriptlang.org) |
| Backend           | [Rust](https://www.rust-lang.org)              |
| Async runtime     | [Tokio](https://tokio.rs)                      |
| Download engine   | Custom Aria2 Next C++ sidecar                  |
| UI components     | [Material Web](https://material-web.dev)       |
| Styling           | [Tailwind CSS 4](https://tailwindcss.com)      |
| State management  | [Zustand](https://github.com/pmndrs/zustand)   |
| Server state      | [TanStack Query](https://tanstack.com/query)   |
| Database          | SQLite through `tauri-plugin-sql`              |
| Icons             | [Solar Icons](https://solar-icons.com)         |

---

## Architecture

FF Downloader uses a layered desktop architecture:

```text
┌─────────────────────────────────────────────┐
│              Next.js Frontend               │
│                                             │
│  React UI · Zustand · TanStack Query        │
└──────────────────────┬──────────────────────┘
                       │
                 Tauri IPC Commands
                       │
┌──────────────────────▼──────────────────────┐
│               Rust Backend                  │
│                                             │
│  Services · Database · Engine Management    │
└──────────────────────┬──────────────────────┘
                       │
                  JSON-RPC / IPC
                       │
┌──────────────────────▼──────────────────────┐
│         Custom Aria2 Next Sidecar           │
│                                             │
│  HTTP · BitTorrent · Metalink · ED2K        │
└─────────────────────────────────────────────┘
```

The frontend handles presentation and user interaction. Tauri commands connect the frontend to the Rust backend, while the backend manages persistence, system integration, and the download engine lifecycle.

---

## Project Structure

```text
.
├── src/
│   ├── app/                     # Next.js App Router pages
│   ├── components/              # Reusable React components
│   ├── hooks/                   # Shared React hooks
│   ├── lib/                     # Frontend utilities
│   ├── services/                # Frontend service layer
│   ├── stores/                  # Zustand stores
│   └── types/                   # TypeScript definitions
│
├── src-tauri/
│   ├── src/
│   │   ├── aria2/               # Aria2 JSON-RPC client
│   │   ├── commands/            # Tauri IPC command modules
│   │   ├── engine/              # Download engine lifecycle
│   │   └── services/            # Background system services
│   │
│   ├── binaries/                # Prebuilt engine sidecars
│   ├── capabilities/            # Tauri v2 permissions
│   ├── migrations/              # SQLite migrations
│   └── tauri.conf.json          # Tauri configuration
│
├── public/                       # Static frontend assets
├── package.json
└── README.md
```

---

## Development Commands

| Command            | Description                             |
| ------------------ | --------------------------------------- |
| `pnpm install`     | Install project dependencies            |
| `pnpm tauri:dev`   | Run the application in development mode |
| `pnpm tauri:build` | Build production installers             |
| `pnpm lint`        | Run frontend lint checks                |
| `pnpm typecheck`   | Run TypeScript type checking            |

> Available commands may depend on the scripts configured in `package.json`.

---

## Star History

<div align="center">

## Star History

<a href="https://www.star-history.com/?repos=Riteshp2001%2FFucking-Fast-Downloader&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=Riteshp2001/Fucking-Fast-Downloader&type=date&theme=dark&legend=top-left&sealed_token=igsKa1AykTExGa_Adx0yQsBXun3ayXyITNhYeaoqIz-rifRSWyPzAHCHEfwYg4IrmNEB_sW5WNo9A9qLjQBdihyVmN4Ku61pjKwf4nmR8kUlGbol1EOYiw" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=Riteshp2001/Fucking-Fast-Downloader&type=date&legend=top-left&sealed_token=igsKa1AykTExGa_Adx0yQsBXun3ayXyITNhYeaoqIz-rifRSWyPzAHCHEfwYg4IrmNEB_sW5WNo9A9qLjQBdihyVmN4Ku61pjKwf4nmR8kUlGbol1EOYiw" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=Riteshp2001/Fucking-Fast-Downloader&type=date&legend=top-left&sealed_token=igsKa1AykTExGa_Adx0yQsBXun3ayXyITNhYeaoqIz-rifRSWyPzAHCHEfwYg4IrmNEB_sW5WNo9A9qLjQBdihyVmN4Ku61pjKwf4nmR8kUlGbol1EOYiw" />
 </picture>
</a>

</div>

---

## Contributing

Contributions are welcome.

Before submitting a change:

1. Fork the repository.
2. Create a new branch.
3. Make and test your changes.
4. Follow the existing project structure and code style.
5. Open a pull request with a clear explanation of the change.

```bash
git checkout -b feature/your-feature-name
```

For bugs and feature requests, open an issue through the [GitHub issue tracker](https://github.com/Riteshp2001/Fucking-Fast-Downloader/issues).

---

## Support

FF Downloader is an independently developed open-source project.

Supporting the project helps fund continued development, testing, maintenance, and platform-specific releases.

<div align="center">

[![Buy Me a Coffee](https://img.shields.io/badge/Support_the_Project-FFDD00?style=for-the-badge\&logo=buy-me-a-coffee\&logoColor=black)](https://buymeacoffee.com/riteshp2001/e/367661)

</div>

---

## License

FF Downloader is distributed under the MIT License.

See the [LICENSE](./LICENSE) file for complete license information.

---

## Author

Created and maintained by [Ritesh Pandit](https://github.com/Riteshp2001).

<div align="center">

**Built for faster and more reliable downloads.**

[GitHub](https://github.com/Riteshp2001) ·
[Releases](https://github.com/Riteshp2001/Fucking-Fast-Downloader/releases) ·
[Report an Issue](https://github.com/Riteshp2001/Fucking-Fast-Downloader/issues)

</div>
