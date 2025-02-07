#!/usr/bin/env python3
"""
Fucking Fast Downloader
A PyQt5 application to download files from provided links.

Usage:
  - Click "Load Links" to import download links from input.txt.
  - Double-click any link in the list to copy it to clipboard.
  - Click "Download All" to start downloading.
  - Use the Pause/Resume buttons to control the downloads.
"""

import os
import re
import sys
import time
import webbrowser
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QFontDatabase
from qt_material import apply_stylesheet

# Global configuration
INPUT_FILE = "input.txt"
DOWNLOADS_FOLDER = "downloads"

if not os.path.exists(DOWNLOADS_FOLDER):
    os.makedirs(DOWNLOADS_FOLDER)

HEADERS = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'accept-language': 'en-US,en;q=0.5',
    'referer': 'https://fitgirl-repacks.site/',
    'sec-ch-ua': '"Brave";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'user-agent': (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
}

# ---------------------------------------------------------------------------
# Helper function to colorize log messages based on content.
def colorize_log_message(message):
    """
    Return the message wrapped in an HTML span with a color and emoji
    based on keywords in the message.
    """
    msg_lower = message.lower()
    emoji = ""
    
    if "error" in msg_lower or "❌" in message:
        color = "#FF6347"  # Tomato
        if "❌" not in message:
            emoji = "❌ "
    elif "completed" in msg_lower or "✅" in message:
        color = "#32CD32"  # LimeGreen
        if "✅" not in message:
            emoji = "✅ "
    elif "paused" in msg_lower:
        color = "#FFD700"  # Gold
        if "⏸️" not in message:
            emoji = "⏸️ "
    elif "resumed" in msg_lower:
        color = "#00BFFF"  # DeepSkyBlue
        if "▶️" not in message:
            emoji = "▶️ "
    elif "downloading" in msg_lower or "⬇️" in message:
        color = "#1E90FF"  # DodgerBlue
        if "⬇️" not in message:
            emoji = "⬇️ "
    elif "processing link" in msg_lower:
        color = "#40E0D0"  # Turquoise
        if "🔗" not in message:
            emoji = "🔗 "
    elif "loaded" in msg_lower:
        color = "#DA70D6"  # Orchid
        if "📥" not in message:
            emoji = "📥 "
    else:
        color = "#FFFFFF"  # Default to white if no keywords match

    return f"<span style='color:{color};'>{emoji}{message}</span>"

# ----------------------- GUI Code -----------------------
class DownloaderWorker(QtCore.QThread):
    """
    Worker thread that processes download links and downloads files.
    """
    log_signal = QtCore.pyqtSignal(str)
    progress_signal = QtCore.pyqtSignal(int, int)  # downloaded, total
    file_signal = QtCore.pyqtSignal(str)
    status_signal = QtCore.pyqtSignal(str)
    speed_signal = QtCore.pyqtSignal(float)
    link_removed_signal = QtCore.pyqtSignal(str)

    def __init__(self, links, parent=None):
        super().__init__(parent)
        self.links = links
        self._is_paused = False

    def pause(self):
        """Pause the ongoing download."""
        self._is_paused = True
        self.status_signal.emit("Paused")
        self.log_signal.emit("Download paused.")

    def resume_download(self):
        """Resume a paused download."""
        self._is_paused = False
        self.status_signal.emit("Downloading...")
        self.log_signal.emit("Download resumed.")

    def run(self):
        """Process each link: fetch, parse, and download the file."""
        for link in self.links:
            self.log_signal.emit(f"Processing link:\n  {link}")
            try:
                response = requests.get(link, headers=HEADERS)
            except Exception as e:
                self.log_signal.emit(f"Error fetching link:\n  {link}\n  {e}")
                continue

            if response.status_code != 200:
                self.log_signal.emit(f"Failed to retrieve link ({response.status_code}):\n  {link}")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            meta_title = soup.find('meta', attrs={'name': 'title'})
            file_name = meta_title['content'] if meta_title else "default_file_name"

            # Search for a download URL in the script tags.
            download_url = None
            for script in soup.find_all('script'):
                if 'function download' in script.text:
                    match = re.search(r'window\.open\(["\'](https?://[^\s"\'\)]+)', script.text)
                    if match:
                        download_url = match.group(1)
                    break

            if not download_url:
                self.log_signal.emit(f"Download URL not found for link:\n  {link}")
                continue

            self.log_signal.emit(f"Downloading '{file_name}' from:\n  {download_url[:70]}...")
            output_path = os.path.join(DOWNLOADS_FOLDER, file_name)
            self.file_signal.emit(os.path.basename(output_path))
            try:
                self.download_file(download_url, output_path)
                self.link_removed_signal.emit(link)
            except Exception as e:
                self.log_signal.emit(f"Error downloading '{file_name}': {e}")

        self.status_signal.emit("All downloads completed.")
        self.log_signal.emit("All downloads have been processed.")

    def download_file(self, download_url, output_path):
        """
        Download a file from the specified URL and save it to the given path.
        """
        self.status_signal.emit("Downloading...")
        response = requests.get(download_url, stream=True)
        if response.status_code != 200:
            raise Exception(f"HTTP Error: {response.status_code}")

        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024
        downloaded = 0
        start_time = time.time()

        with open(output_path, 'wb') as f:
            for data in response.iter_content(block_size):
                while self._is_paused:
                    self.msleep(100)
                if data:
                    f.write(data)
                    downloaded += len(data)
                    elapsed = time.time() - start_time
                    speed = downloaded / elapsed if elapsed > 0 else 0
                    self.progress_signal.emit(downloaded, total_size)
                    self.speed_signal.emit(speed / 1024)
        self.status_signal.emit("Download completed")
        self.log_signal.emit(f"Download completed: {output_path}")


class MainWindow(QtWidgets.QMainWindow):
    """
    Main application window for the downloader.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fucking Fast Downloader")
        self.resize(850, 600)
        self.setStatusBar(QtWidgets.QStatusBar(self))  # For transient notifications

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        main_layout = QtWidgets.QVBoxLayout(central)

        # Determine base path for resources.
        self.base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))

        try:
            icon_path = os.path.join(self.base_path, "icons", "fuckingfast.ico")
            self.setWindowIcon(QtGui.QIcon(icon_path))
        except Exception as e:
            print(f"Error loading icon: {e}")

        # Set the default application font.
        nice_font = "Roboto" if "Roboto" in QFontDatabase().families() else "Segoe UI"
        QtWidgets.QApplication.setFont(QFont(nice_font, 10))

        # Top buttons.
        top_button_layout = QtWidgets.QHBoxLayout()
        self.load_btn = QtWidgets.QPushButton("Load Links")
        self.download_btn = QtWidgets.QPushButton("Download All")
        top_button_layout.addWidget(self.load_btn)
        top_button_layout.addWidget(self.download_btn)
        main_layout.addLayout(top_button_layout)

        # Usage instructions.
        # self.usage_label = QtWidgets.QLabel(
        #     "Usage: Click 'Load Links' to import download links from input.txt. "
        #     "Double-click any link to copy it to clipboard. "
        #     "Click 'Download All' to start downloading. Use Pause/Resume to control downloads."
        # )
        # self.usage_label.setStyleSheet("color: #CCCCCC; font-size: 12px; margin-bottom: 10px;")
        # main_layout.addWidget(self.usage_label)

        # Main content layout.
        content_layout = QtWidgets.QHBoxLayout()
        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.setToolTip("List of download links. Double-click an item to copy the link.")
        content_layout.addWidget(self.list_widget, 1)
        self.list_widget.itemDoubleClicked.connect(self.copy_link_to_clipboard)

        # Right-side layout for progress and logs.
        right_layout = QtWidgets.QVBoxLayout()
        self.file_label = QtWidgets.QLabel("📁 Current File: None")
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setFormat("%v / %m bytes")

        pause_resume_layout = QtWidgets.QHBoxLayout()
        self.pause_btn = QtWidgets.QPushButton("▶ Pause")
        self.pause_btn.setObjectName("pause_btn")
        self.resume_btn = QtWidgets.QPushButton("⏸ Resume")
        self.resume_btn.setObjectName("resume_btn")
        pause_resume_layout.addWidget(self.pause_btn)
        pause_resume_layout.addWidget(self.resume_btn)

        self.status_label = QtWidgets.QLabel("🟢 Status: Idle")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #4CAF50;")

        self.progress_detail_label = QtWidgets.QLabel(
            "⬇️ Downloaded: 0.00 MB\n"
            "📦 Total: 0.00 MB\n"
            "⏳ Remaining: 0.00 MB"
        )
        self.progress_detail_label.setStyleSheet("font-weight: 500;")

        self.speed_label = QtWidgets.QLabel("🚀 Speed: 0.00 KB/s")
        self.speed_label.setStyleSheet("font-weight: 500; color: #FF5722;")

        self.log_text = QtWidgets.QTextEdit()
        self.log_text.setReadOnly(True)
        # Enable rich text for HTML content.
        self.log_text.setAcceptRichText(True)
        self.log_text.setFont(QtGui.QFont("Segoe UI", 12))

        right_layout.addWidget(self.file_label)
        right_layout.addWidget(self.progress_bar)
        right_layout.addLayout(pause_resume_layout)
        right_layout.addWidget(self.progress_detail_label)
        right_layout.addWidget(self.speed_label)
        right_layout.addWidget(self.status_label)
        right_layout.addWidget(self.log_text, 1)
        content_layout.addLayout(right_layout, 2)
        main_layout.addLayout(content_layout)

        # Bottom layout for support buttons.
        self.github_button = QtWidgets.QPushButton()
        github_icon = os.path.join(self.base_path, "icons", "github.png")
        self.github_button.setIcon(QtGui.QIcon(github_icon))
        self.github_button.setIconSize(QtCore.QSize(64, 64))
        self.github_button.setToolTip("View Source Code on Github 🐙")
        self.github_button.setStyleSheet("""
            QPushButton {
                border: none;
                margin: 10px;
                padding: 5px 0;
                background-color: transparent;
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 0.1); }
        """)
        self.github_button.clicked.connect(
            lambda: webbrowser.open("https://github.com/Riteshp2001/Fucking-Fast-Downloader")
        )

        self.buymecoffee_button = QtWidgets.QPushButton()
        buymecoffee_icon = os.path.join(self.base_path, "icons", "buymecoffee.png")
        self.buymecoffee_button.setIcon(QtGui.QIcon(buymecoffee_icon))
        self.buymecoffee_button.setIconSize(QtCore.QSize(64, 64))
        self.buymecoffee_button.setToolTip("Just Buy me a Coffee ☕ Already !!")
        self.buymecoffee_button.setStyleSheet("""
            QPushButton {
                border: none;
                margin: 10px;
                padding: 5px 0;
                background-color: transparent;
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 0.1); }
        """)
        self.buymecoffee_button.clicked.connect(
            lambda: webbrowser.open("https://buymeacoffee.com/riteshp2001/e/367661")
        )

        self.support = QtWidgets.QLabel(
            "Support My Work on Buy Me a Coffee & Check Out What I've Been Up To on Github! 🫡"
        )
        self.support.setAlignment(Qt.AlignCenter)
        self.support.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 10px;")

        bottom_layout = QtWidgets.QHBoxLayout()
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.github_button)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.support)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.buymecoffee_button)
        bottom_layout.addStretch()
        main_layout.addLayout(bottom_layout)

        self.credits_label = QtWidgets.QLabel(
            "Made with <span style='color: #FF6347; font-weight: bold;'>❤️</span> by "
            "<a style='color: #1E90FF; text-decoration: none;' href='https://riteshpandit.vercel.app'>Ritesh Pandit</a>"
        )
        self.credits_label.setOpenExternalLinks(True)
        self.credits_label.setAlignment(Qt.AlignCenter)
        self.credits_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 10px;")
        main_layout.addWidget(self.credits_label)

        # Set cursors for interactive elements.
        self.load_btn.setCursor(Qt.PointingHandCursor)
        self.download_btn.setCursor(Qt.PointingHandCursor)
        self.pause_btn.setCursor(Qt.PointingHandCursor)
        self.resume_btn.setCursor(Qt.PointingHandCursor)
        self.github_button.setCursor(Qt.PointingHandCursor)
        self.buymecoffee_button.setCursor(Qt.PointingHandCursor)
        self.list_widget.setCursor(Qt.ArrowCursor)

        # Application-wide stylesheet.
        self.setStyleSheet("""
            QPushButton {
                background-color: #2B579A;
                color: white;
                border: 1px solid #1D466B;
                border-radius: 4px;
                padding: 8px 16px;
                margin: 2px;
            }
            QPushButton:hover {
                background-color: #3C6AAA;
                border: 1px solid #2B579A;
            }
            QPushButton:pressed { background-color: #1D466B; }
            QPushButton#pause_btn { background-color: #FF5722; }
            QPushButton#pause_btn:hover { background-color: #FF7043; }
            QPushButton#resume_btn { background-color: #4CAF50; }
            QPushButton#resume_btn:hover { background-color: #66BB6A; }
            QListWidget {
                background-color: #1E1E1E;
                color: #FFFFFF;
                border: 1px solid #3C3C3C;
                border-radius: 4px;
            }
            QListWidget::item:hover { background-color: #3C3C3C; }
            QListWidget::item:selected { background-color: #2B579A; }
            QProgressBar {
                border: 1px solid #3C3C3C;
                border-radius: 4px;
                text-align: center;
                background-color: #1E1E1E;
            }
            QProgressBar::chunk {
                background-color: #2B579A;
                border-radius: 4px;
            }
            QTextEdit {
                background-color: #1E1E1E;
                color: #FFFFFF;
                border: 1px solid #3C3C3C;
                border-radius: 4px;
            }
            QLabel { color: #FFFFFF; }
        """)

        # Connect button signals.
        self.load_btn.clicked.connect(self.load_links)
        self.download_btn.clicked.connect(self.download_all)
        self.pause_btn.clicked.connect(self.pause_download)
        self.resume_btn.clicked.connect(self.resume_download)

        self.worker = None

    def load_links(self):
        if not os.path.exists(INPUT_FILE):
            with open(INPUT_FILE, 'w') as f:
                f.write("# Add download links here (remove this line and add links only)\n")
            QtWidgets.QMessageBox.information(self, "Info", f"Input file '{INPUT_FILE}' not found. It has been created.")
            return

        self.list_widget.clear()
        with open(INPUT_FILE, 'r') as f:
            links = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
        for idx, link in enumerate(links, start=1):
            self.list_widget.addItem(f"{idx}. {link}")
        self.log(f"Loaded {len(links)} link(s) from {INPUT_FILE}")

    def copy_link_to_clipboard(self, item):
        parts = item.text().split(". ", 1)
        link = parts[1] if len(parts) == 2 else item.text()
        QtWidgets.QApplication.clipboard().setText(link)
        self.statusBar().showMessage("Link copied to clipboard", 2000)

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        colored_message = colorize_log_message(message)
        self.log_text.append(f"<p style='font-weight:600; font-family: \"Segoe UI\"; font-size:12px;'><span style='color:gray;'>[{timestamp}]</span> {colored_message}</p>")

    def download_all(self):
        links = []
        for i in range(self.list_widget.count()):
            item_text = self.list_widget.item(i).text()
            parts = item_text.split(". ", 1)
            links.append(parts[1] if len(parts) == 2 else item_text)

        if not links:
            QtWidgets.QMessageBox.information(self, "Info", "No links to download.")
            return

        self.worker = DownloaderWorker(links)
        self.worker.log_signal.connect(self.log)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.file_signal.connect(self.update_file)
        self.worker.status_signal.connect(self.update_status)
        self.worker.speed_signal.connect(self.update_speed)
        self.worker.link_removed_signal.connect(self.remove_link_from_list)
        self.worker.start()

    def pause_download(self):
        if self.worker and self.worker.isRunning():
            self.worker.pause()

    def resume_download(self):
        if self.worker and self.worker.isRunning():
            self.worker.resume_download()

    def update_progress(self, downloaded, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(downloaded)
        downloaded_mb = downloaded / (1024 * 1024)
        total_mb = total / (1024 * 1024)
        remaining_mb = total_mb - downloaded_mb
        self.progress_detail_label.setText(
            f"Downloaded: {downloaded_mb:.2f} MB / {total_mb:.2f} MB\nRemaining: {remaining_mb:.2f} MB"
        )

    def update_file(self, filename):
        self.file_label.setText(f"📁 Current File: {filename}")

    def update_status(self, status):
        self.status_label.setText(f"Status: {status}")

    def update_speed(self, speed):
        if speed > 1024:
            self.speed_label.setText(f"Speed: {speed/1024:.2f} MB/s")
        else:
            self.speed_label.setText(f"Speed: {speed:.2f} KB/s")

    def remove_link_from_list(self, link):
        for i in range(self.list_widget.count()):
            item_text = self.list_widget.item(i).text()
            if item_text.split(". ", 1)[-1] == link:
                self.list_widget.takeItem(i)
                break
        if os.path.exists(INPUT_FILE):
            with open(INPUT_FILE, 'r') as f:
                lines = f.readlines()
            with open(INPUT_FILE, 'w') as f:
                for line in lines:
                    if line.strip() != link:
                        f.write(line)

# --------------------- End of GUI Code ---------------------

def main():
    app = QtWidgets.QApplication(sys.argv)
    default_font = QFont("Roboto" if "Roboto" in QFontDatabase().families() else "Segoe UI", 10)
    app.setFont(default_font)
    apply_stylesheet(app, theme='dark_blue.xml')
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
