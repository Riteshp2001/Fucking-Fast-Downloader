import os
import sys

from PyQt5 import QtCore, QtGui, QtWidgets

from ff_downloader.ui import MainWindow
from ff_downloader.ui.brand_assets import application_icon


def _configure_high_dpi() -> None:
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

    policy_enum = getattr(QtCore.Qt, "HighDpiScaleFactorRoundingPolicy", None)
    setter = getattr(QtWidgets.QApplication, "setHighDpiScaleFactorRoundingPolicy", None)
    if policy_enum is not None and setter is not None:
        setter(policy_enum.PassThrough)


def main() -> int:
    _configure_high_dpi()
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Fucking Fast Downloader")
    app.setOrganizationName("Riteshp2001")
    app.setFont(QtGui.QFont("Segoe UI", 10))
    app.setWindowIcon(application_icon())
    window = MainWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
