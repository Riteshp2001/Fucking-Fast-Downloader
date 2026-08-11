import sys

from PyQt5 import QtCore, QtGui, QtWidgets

from ff_downloader.ui import MainWindow


def main() -> int:
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps)
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Fucking Fast Downloader")
    app.setFont(QtGui.QFont("Segoe UI", 10))
    window = MainWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
