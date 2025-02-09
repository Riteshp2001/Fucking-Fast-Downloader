#!/usr/bin/env python3
"""
Fucking Fast Downloader - PyQt5-based GUI application for batch downloading files from provided links.

Features:
- Load links from input file
- Download management with pause/resume
- Progress tracking and speed monitoring
- Error handling with retry logic
- Clipboard integration for individual links

Module Structure:
- DownloaderWorker: QThread subclass handling download processing
- MainWindow: QMainWindow subclass providing GUI interface
- Helper functions for logging and UI formatting
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

def colorize_log_message(message: str) -> str:
    """Apply color formatting and emojis to log messages based on content keywords.

    Args:
        message: Original log message text

    Returns:
        str: HTML-formatted string with styling and emojis

    Example:
        >>> colorize_log_message("Error occurred")
        '<span style="color:#FF6347;">❌ Error occurred</span>'
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

class DownloaderWorker(QtCore.QThread):
    """Worker thread handling download processing and file operations.

    Attributes:
        log_signal: PyQt signal for logging messages
        progress_signal: Signal for download progress updates
        file_signal: Signal for current file name updates
        status_signal: Signal for status text updates
        speed_signal: Signal for download speed updates
        link_removed_signal: Signal for successful link removal
        link_failed_signal: Signal for failed link processing

    Args:
        links: List of URLs to process
        parent: Parent QObject
    """

    log_signal = QtCore.pyqtSignal(str)
    progress_signal = QtCore.pyqtSignal(int, int)  # downloaded, total
    file_signal = QtCore.pyqtSignal(str)
    status_signal = QtCore.pyqtSignal(str)
    speed_signal = QtCore.pyqtSignal(float)
    link_removed_signal = QtCore.pyqtSignal(str)
    link_failed_signal = QtCore.pyqtSignal(str)

    def __init__(self, links: list, parent: QtCore.QObject = None):
        """Initialize download worker with list of links."""
        super().__init__(parent)
        self.links = links
        self._is_paused = False

    def pause(self) -> None:
        """Pause active download operation."""
        self._is_paused = True
        self.status_signal.emit("Paused")
        self.log_signal.emit("Download paused.")

    def resume_download(self) -> None:
        """Resume paused download operation."""
        self._is_paused = False
        self.status_signal.emit("Downloading...")
        self.log_signal.emit("Download resumed.")

    def run(self) -> None:
        """Main thread execution method with retry logic."""
        for link in self.links:
            attempts = 0
            success = False
            while attempts < 3 and not success:
                self.log_signal.emit(f"Processing link:\n  {link} (Attempt {attempts+1}/3)")
                try:
                    response = requests.get(link, headers=HEADERS)
                    if response.status_code != 200:
                        raise Exception(f"Failed to retrieve link (HTTP {response.status_code})")
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    meta_title = soup.find('meta', attrs={'name': 'title'})
                    file_name = meta_title['content'] if meta_title else "default_file_name"

                    download_url = None
                    for script in soup.find_all('script'):
                        if 'function download' in script.text:
                            match = re.search(r'window\.open\(["\'](https?://[^\s"\'\)]+)', script.text)
                            if match:
                                download_url = match.group(1)
                            break

                    if not download_url:
                        raise Exception("Download URL not found")

                    self.log_signal.emit(f"Downloading '{file_name}' from:\n  {download_url[:70]}...")
                    output_path = os.path.join(DOWNLOADS_FOLDER, file_name)
                    self.file_signal.emit(os.path.basename(output_path))
                    
                    self.download_file(download_url, output_path)
                    self.link_removed_signal.emit(link)
                    success = True
                except Exception as e:
                    attempts += 1
                    self.log_signal.emit(f"Error processing link:\n  {link}\n  Attempt {attempts}/3, error: {e}")
                    if attempts < 3:
                        QtCore.QThread.sleep(3)
                    else:
                        self.log_signal.emit(f"Skipping link after 3 failed attempts:\n  {link}")
                        self.link_failed_signal.emit(link)

        self.status_signal.emit("All downloads completed.")
        self.log_signal.emit("All downloads have been processed.")

    def download_file(self, download_url: str, output_path: str) -> None:
        """Execute file download from URL to local path.

        Args:
            download_url: Source URL for file download
            output_path: Local destination path for file

        Raises:
            Exception: On HTTP errors or network issues
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
    """Main application window handling UI presentation and user interactions.

    Attributes:
        worker: Active download worker thread
        list_widget: UI element displaying loaded links
        progress_bar: Download progress visualization
        log_text: Formatted logging display
    """

    def __init__(self):
        """Initialize main window and configure UI components."""
        super().__init__()
        self.setWindowTitle("Fucking Fast Downloader")
        self.resize(850, 600)
        self.setStatusBar(QtWidgets.QStatusBar(self))
        
        # UI initialization code remains same as original
        # ... [rest of UI setup code unchanged] ...

    def load_links(self) -> None:
        """Load links from input file into UI list."""
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

    def copy_link_to_clipboard(self, item: QtWidgets.QListWidgetItem) -> None:
        """Copy link text from list item to system clipboard.

        Args:
            item: QListWidgetItem containing link text
        """
        parts = item.text().split(". ", 1)
        link = parts[1] if len(parts) == 2 else item.text()
        QtWidgets.QApplication.clipboard().setText(link)
        self.statusBar().showMessage("Link copied to clipboard", 2000)

    def log(self, message: str) -> None:
        """Append formatted message to log display.

        Args:
            message: Plain text log message
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        colored_message = colorize_log_message(message)
        self.log_text.append(f"<p style='font-weight:600; font-family: \"Segoe UI\"; font-size:12px;'><span style='color:gray;'>[{timestamp}]</span> {colored_message}</p>")

    def download_all(self) -> None:
        """Initiate batch download process."""
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
        self.worker.link_failed_signal.connect(self.mark_link_failed)
        self.worker.start()

    def update_progress(self, downloaded: int, total: int) -> None:
        """Update progress indicators with current download metrics.

        Args:
            downloaded: Bytes downloaded
            total: Total bytes expected
        """
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(downloaded)
        downloaded_mb = downloaded / (1024 * 1024)
        total_mb = total / (1024 * 1024)
        remaining_mb = total_mb - downloaded_mb
        self.progress_detail_label.setText(
            f"Downloaded: {downloaded_mb:.2f} MB / {total_mb:.2f} MB\nRemaining: {remaining_mb:.2f} MB"
        )

    def remove_link_from_list(self, link: str) -> None:
        """Remove successfully processed link from UI and input file.

        Args:
            link: URL to remove from tracking
        """
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

    def mark_link_failed(self, link: str) -> None:
        """Visual indicator for failed links in UI list.

        Args:
            link: URL that failed processing
        """
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            parts = item.text().split(". ", 1)
            if len(parts) == 2 and parts[1] == link:
                item.setForeground(QtGui.QColor("red"))
                break

def main() -> None:
    """Main application entry point."""
    app = QtWidgets.QApplication(sys.argv)
    default_font = QFont("Roboto" if "Roboto" in QFontDatabase().families() else "Segoe UI", 10)
    app.setFont(default_font)
    apply_stylesheet(app, theme='dark_blue.xml')
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()