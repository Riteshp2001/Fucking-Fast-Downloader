import sys
import os
import re
import time
import webbrowser
import requests
from datetime import datetime

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QApplication
from qt_material import apply_stylesheet
from bs4 import BeautifulSoup
from PyQt5.QtGui import QFont, QFontDatabase

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
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
}


class DownloaderWorker(QtCore.QThread):
    # Signals to communicate with the UI.
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
        self._is_paused = True
        self.status_signal.emit("Paused")
        self.log_signal.emit("Download paused.")

    def resume_download(self):
        self._is_paused = False
        self.status_signal.emit("Downloading...")
        self.log_signal.emit("Download resumed.")

    def run(self):
        for link in self.links:
            self.log_signal.emit(f"Processing link:\n  {link}")
            try:
                response = requests.get(link, headers=HEADERS)
            except Exception as e:
                self.log_signal.emit(f"Error fetching link:\n  {link}\n  {str(e)}")
                continue

            if response.status_code != 200:
                self.log_signal.emit(f"Failed to retrieve link ({response.status_code}):\n  {link}")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            meta_title = soup.find('meta', attrs={'name': 'title'})
            file_name = meta_title['content'] if meta_title else "default_file_name"

            # Look for a download URL in script tags.
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
                # After a successful download, emit a signal to remove the link.
                self.link_removed_signal.emit(link)
            except Exception as e:
                self.log_signal.emit(f"Error downloading '{file_name}': {str(e)}")
        self.status_signal.emit("All downloads completed.")
        self.log_signal.emit("All downloads have been processed.")

    def download_file(self, download_url, output_path):
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
                # Check pause state.
                while self._is_paused:
                    self.msleep(100)  # sleep for 100 ms when paused
                if data:
                    f.write(data)
                    downloaded += len(data)
                    elapsed = time.time() - start_time
                    speed = downloaded / elapsed if elapsed > 0 else 0
                    # Emit progress and speed signals.
                    self.progress_signal.emit(downloaded, total_size)
                    self.speed_signal.emit(speed / 1024)
        self.status_signal.emit("Download completed")
        self.log_signal.emit(f"Download completed: {output_path}")


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fucking Fast Downloader")
        self.resize(850, 600)
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        main_layout = QtWidgets.QVBoxLayout(central)

        # Add this resource handling
        if getattr(sys, 'frozen', False):
            self.base_path = sys._MEIPASS
        else:
            self.base_path = os.path.abspath(".")

        try:        
            self.setWindowIcon(QtGui.QIcon(os.path.join(self.base_path, "icons", "fuckingfast.ico")))
        except Exception as e:
            print(f"Error loading icon: {str(e)}")

        # First try to load a modern font
        font_family = "Segoe UI"  # Windows modern font
        if "Inter" in QFontDatabase().families():  # Try Inter font if installed
            font_family = "Inter"
        elif "SF Pro" in QFontDatabase().families():  # macOS system font
            font_family = "SF Pro"
        else:
            font_family = "Consolas" if "Consolas" in QFontDatabase().families() else "Sans Serif"

        # Set default font for the application
        default_font = QFont(font_family, 10)
        QApplication.setFont(default_font)

        # Top button layout.
        top_button_layout = QtWidgets.QHBoxLayout()
        self.load_btn = QtWidgets.QPushButton("Load Links")
        self.download_btn = QtWidgets.QPushButton("Download All")
        top_button_layout.addWidget(self.load_btn)
        top_button_layout.addWidget(self.download_btn)
        main_layout.addLayout(top_button_layout)

        # Main content layout: left side for links, right side for progress and logs.
        content_layout = QtWidgets.QHBoxLayout()
        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.setToolTip("List of download links.")
        content_layout.addWidget(self.list_widget, 1)

        # Right-side vertical layout.
        right_layout = QtWidgets.QVBoxLayout()
        self.file_label = QtWidgets.QLabel("File: None")
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setFormat("%v / %m bytes")
        # Horizontal layout for Pause and Resume buttons beside progress bar.
        pause_resume_layout = QtWidgets.QHBoxLayout()
        self.pause_btn = QtWidgets.QPushButton("▶ Pause")
        self.resume_btn = QtWidgets.QPushButton("⏸ Resume")
        pause_resume_layout.addWidget(self.pause_btn)
        pause_resume_layout.addWidget(self.resume_btn)
        # Detailed progress label.
        self.status_label = QtWidgets.QLabel("🟢 Status: Idle")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #4CAF50;")
        self.file_label = QtWidgets.QLabel("📁 Current File: None")
        self.file_label.setStyleSheet("font-weight: bold;")

        # Progress Section
        self.progress_detail_label = QtWidgets.QLabel(
            "⬇️ Downloaded: 0.00 MB\n"
            "📦 Total: 0.00 MB\n"
            "⏳ Remaining: 0.00 MB"
        )
        self.progress_detail_label.setStyleSheet("font-weight: 500;")
        self.speed_label = QtWidgets.QLabel("🚀 Speed: 0.00 KB/s")
        self.speed_label.setStyleSheet("font-weight: 500; color: #FF5722;")
        # Log Section
        self.log_text = QtWidgets.QTextEdit()
        self.log_text.setReadOnly(True)
        # Set a monospaced font for the log console.
        mono_font = QtGui.QFont("Segoe UI", 12)
        self.log_text.setFont(mono_font)

        right_layout.addWidget(self.file_label)
        right_layout.addWidget(self.progress_bar)
        right_layout.addLayout(pause_resume_layout)
        right_layout.addWidget(self.progress_detail_label)
        right_layout.addWidget(self.speed_label)
        right_layout.addWidget(self.status_label)
        right_layout.addWidget(self.log_text, 1)

        content_layout.addLayout(right_layout, 2)
        main_layout.addLayout(content_layout)

        self.github_button = QtWidgets.QPushButton()        
        self.github_button.setIcon(QtGui.QIcon(os.path.join(self.base_path, "icons", "github.png")))
        self.github_button.setIconSize(QtCore.QSize(64, 64))  # Increased icon size for better visibility
        self.github_button.setToolTip("View Source Code on Github 🐙")
        self.github_button.setStyleSheet("""
            border: none;
            margin: 10px;
            padding: 5px 0px;
            background-color: transparent;
        """)
        self.github_button.clicked.connect(lambda: webbrowser.open("https://github.com/Riteshp2001/Fucking-Fast-Downloader"))

        self.buymecoffee_button = QtWidgets.QPushButton()        
        self.buymecoffee_button.setIcon(QtGui.QIcon(os.path.join(self.base_path, "icons", "buymecoffee.png")))
        self.buymecoffee_button.setIconSize(QtCore.QSize(64, 64))  # Increased icon size for better visibility
        self.buymecoffee_button.setToolTip("Just Buy me a Coffee ☕ Already !!")
        self.buymecoffee_button.setStyleSheet("""
            border: none;
            margin: 10px;
            padding: 5px 0px;
            background-color: transparent;
        """)
        self.buymecoffee_button.clicked.connect(lambda: webbrowser.open("https://buymeacoffee.com/riteshp2001/e/367661"))

        self.support = QtWidgets.QLabel("Support My Work on Buy Me a Coffee & Check Out What I've Been Up To on Github! 🫡")
        self.support.setAlignment(QtCore.Qt.AlignCenter)
        self.support.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 10px;")

        # Layout adjustments
        bottom_layout = QtWidgets.QHBoxLayout()

        # Adding spacers and widgets for equal alignment
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.github_button)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.support)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.buymecoffee_button)
        bottom_layout.addStretch()

        main_layout.addLayout(bottom_layout)

        # "Made with ❤️ by Ritesh Pandit" label
        self.credits_label = QtWidgets.QLabel("Made with <span style='color: #FF6347; font-weight: bold;'>❤️</span> by <a style='color: #1E90FF; text-decoration: none;' href='https://riteshpandit.vercel.app'>Ritesh Pandit</a>")
        self.credits_label.setOpenExternalLinks(True)
        self.credits_label.setAlignment(QtCore.Qt.AlignCenter)
        self.credits_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 10px;")
        main_layout.addWidget(self.credits_label)

        # Connect button signals.
        self.load_btn.clicked.connect(self.load_links)
        self.download_btn.clicked.connect(self.download_all)
        self.pause_btn.clicked.connect(self.pause_download)
        self.resume_btn.clicked.connect(self.resume_download)

        self.worker = None

    def load_links(self):
        if not os.path.exists(INPUT_FILE):
            # Create the input file if it doesn't exist.
            with open(INPUT_FILE, 'w') as f:
                f.write("# Add download links here , remove this line also and paste link only\n")  # You can add some default content if needed.
            QtWidgets.QMessageBox.information(self, "Info", f"Input file '{INPUT_FILE}' not found. It has been created.")
            return

        self.list_widget.clear()
        with open(INPUT_FILE, 'r') as f:
            links = [line.strip() for line in f if line.strip()]
        for idx, link in enumerate(links, start=1):
            self.list_widget.addItem(f"{idx}. {link}")
        self.log(f"Loaded {len(links)} link(s) from {INPUT_FILE}")


    def resource_path(relative_path):
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")

        return os.path.join(base_path, relative_path)
    
    # In the log method
    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        # Add 4 spaces after timestamp
        self.log_text.append(f"[{timestamp}]    {message}")  # Changed from single space to 4 spaces

    def download_all(self):
        # Extract raw links (remove numbering).
        links = []
        for i in range(self.list_widget.count()):
            item_text = self.list_widget.item(i).text()
            parts = item_text.split(". ", 1)
            if len(parts) == 2:
                links.append(parts[1])
            else:
                links.append(item_text)
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
        # Convert values to megabytes.
        downloaded_mb = downloaded / (1024 * 1024)
        total_mb = total / (1024 * 1024)
        remaining_mb = total_mb - downloaded_mb
        self.progress_detail_label.setText(
            f"Downloaded: {downloaded_mb:.2f} MB / {total_mb:.2f} MB\nRemaining: {remaining_mb:.2f} MB"
        )

    def update_file(self, filename):
        self.file_label.setText(f"File: {filename}")

    def update_status(self, status):
        self.status_label.setText(f"Status: {status}")

    # In update_speed method
    def update_speed(self, speed):
        # Convert KB/s to MB/s if over 1024 KB/s
        if speed > 1024:
            self.speed_label.setText(f"Speed: {speed/1024:.2f} MB/s")
        else:
            self.speed_label.setText(f"Speed: {speed:.2f} KB/s")

    def remove_link_from_list(self, link):
        # Remove the link from the list widget.
        for i in range(self.list_widget.count()):
            item_text = self.list_widget.item(i).text()
            if item_text.split(". ", 1)[-1] == link:
                self.list_widget.takeItem(i)
                break
        # Also remove the link from the input file.
        if os.path.exists(INPUT_FILE):
            with open(INPUT_FILE, 'r') as f:
                lines = f.readlines()
            with open(INPUT_FILE, 'w') as f:
                for line in lines:
                    if line.strip() != link:
                        f.write(line)

def main():
    app = QtWidgets.QApplication(sys.argv)
    # Set application font
    font = QtGui.QFont()
    font.setFamily("Segoe UI" if "Segoe UI" in QtGui.QFontDatabase().families() else "Arial")
    font.setPointSize(10)
    app.setFont(font)
    # Apply a Material Design–inspired stylesheet.
    apply_stylesheet(app, theme='dark_blue.xml')
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
