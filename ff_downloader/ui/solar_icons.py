from __future__ import annotations

from PyQt5 import QtCore, QtGui


class SolarIconFactory:
    """Small Solar-style outline icon renderer built from vector primitives."""

    @staticmethod
    def icon(name: str, color: str = "#D8DEE9", size: int = 20) -> QtGui.QIcon:
        pixmap = QtGui.QPixmap(size, size)
        pixmap.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        pen = QtGui.QPen(
            QtGui.QColor(color),
            max(1.6, size / 12),
            QtCore.Qt.SolidLine,
            QtCore.Qt.RoundCap,
            QtCore.Qt.RoundJoin,
        )
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.NoBrush)
        s = float(size)

        def line(x1: float, y1: float, x2: float, y2: float) -> None:
            painter.drawLine(
                QtCore.QPointF(x1 * s, y1 * s),
                QtCore.QPointF(x2 * s, y2 * s),
            )

        if name == "paste":
            painter.drawRoundedRect(QtCore.QRectF(0.25 * s, 0.22 * s, 0.5 * s, 0.6 * s), 0.1 * s, 0.1 * s)
            painter.drawRoundedRect(
                QtCore.QRectF(0.37 * s, 0.11 * s, 0.26 * s, 0.18 * s),
                0.06 * s,
                0.06 * s,
            )
            line(0.36, 0.48, 0.64, 0.48)
            line(0.36, 0.62, 0.58, 0.62)
        elif name == "shield":
            path = QtGui.QPainterPath(QtCore.QPointF(0.5 * s, 0.1 * s))
            path.lineTo(0.78 * s, 0.22 * s)
            path.lineTo(0.74 * s, 0.58 * s)
            path.quadTo(0.68 * s, 0.79 * s, 0.5 * s, 0.9 * s)
            path.quadTo(0.32 * s, 0.79 * s, 0.26 * s, 0.58 * s)
            path.lineTo(0.22 * s, 0.22 * s)
            path.closeSubpath()
            painter.drawPath(path)
            line(0.37, 0.5, 0.47, 0.61)
            line(0.47, 0.61, 0.66, 0.4)
        elif name == "spark":
            line(0.50, 0.12, 0.50, 0.30)
            line(0.50, 0.70, 0.50, 0.88)
            line(0.12, 0.50, 0.30, 0.50)
            line(0.70, 0.50, 0.88, 0.50)
            line(0.23, 0.23, 0.35, 0.35)
            line(0.65, 0.65, 0.77, 0.77)
            line(0.77, 0.23, 0.65, 0.35)
            line(0.35, 0.65, 0.23, 0.77)
            painter.drawEllipse(QtCore.QRectF(0.39 * s, 0.39 * s, 0.22 * s, 0.22 * s))
        elif name == "copy":
            painter.drawRoundedRect(QtCore.QRectF(0.3 * s, 0.28 * s, 0.48 * s, 0.5 * s), 0.09 * s, 0.09 * s)
            painter.drawRoundedRect(QtCore.QRectF(0.18 * s, 0.16 * s, 0.48 * s, 0.5 * s), 0.09 * s, 0.09 * s)
        elif name == "download":
            line(0.5, 0.15, 0.5, 0.6)
            line(0.32, 0.44, 0.5, 0.62)
            line(0.68, 0.44, 0.5, 0.62)
            painter.drawRoundedRect(QtCore.QRectF(0.2 * s, 0.67 * s, 0.6 * s, 0.18 * s), 0.08 * s, 0.08 * s)
        elif name == "folder":
            path = QtGui.QPainterPath(QtCore.QPointF(0.15 * s, 0.3 * s))
            path.lineTo(0.37 * s, 0.3 * s)
            path.lineTo(0.45 * s, 0.2 * s)
            path.lineTo(0.78 * s, 0.2 * s)
            path.quadTo(0.86 * s, 0.2 * s, 0.86 * s, 0.3 * s)
            path.lineTo(0.86 * s, 0.72 * s)
            path.quadTo(0.86 * s, 0.82 * s, 0.76 * s, 0.82 * s)
            path.lineTo(0.24 * s, 0.82 * s)
            path.quadTo(0.14 * s, 0.82 * s, 0.14 * s, 0.72 * s)
            path.closeSubpath()
            painter.drawPath(path)
        elif name == "pause":
            line(0.37, 0.25, 0.37, 0.75)
            line(0.63, 0.25, 0.63, 0.75)
        elif name == "play":
            path = QtGui.QPainterPath(QtCore.QPointF(0.38 * s, 0.25 * s))
            path.lineTo(0.72 * s, 0.5 * s)
            path.lineTo(0.38 * s, 0.75 * s)
            path.closeSubpath()
            painter.drawPath(path)
        elif name == "stop":
            painter.drawRoundedRect(QtCore.QRectF(0.28 * s, 0.28 * s, 0.44 * s, 0.44 * s), 0.08 * s, 0.08 * s)
        elif name == "link":
            painter.drawRoundedRect(QtCore.QRectF(0.13 * s, 0.36 * s, 0.42 * s, 0.24 * s), 0.11 * s, 0.11 * s)
            painter.drawRoundedRect(QtCore.QRectF(0.45 * s, 0.36 * s, 0.42 * s, 0.24 * s), 0.11 * s, 0.11 * s)
            line(0.4, 0.48, 0.6, 0.48)
        elif name == "activity":
            line(0.12, 0.55, 0.3, 0.55)
            line(0.3, 0.55, 0.4, 0.32)
            line(0.4, 0.32, 0.55, 0.7)
            line(0.55, 0.7, 0.68, 0.45)
            line(0.68, 0.45, 0.88, 0.45)
        elif name == "sun":
            painter.drawEllipse(QtCore.QRectF(0.34 * s, 0.34 * s, 0.32 * s, 0.32 * s))
            for x1, y1, x2, y2 in (
                (0.5, 0.08, 0.5, 0.22),
                (0.5, 0.78, 0.5, 0.92),
                (0.08, 0.5, 0.22, 0.5),
                (0.78, 0.5, 0.92, 0.5),
                (0.2, 0.2, 0.3, 0.3),
                (0.7, 0.7, 0.8, 0.8),
                (0.8, 0.2, 0.7, 0.3),
                (0.3, 0.7, 0.2, 0.8),
            ):
                line(x1, y1, x2, y2)
        elif name == "moon":
            path = QtGui.QPainterPath(QtCore.QPointF(0.67 * s, 0.16 * s))
            path.cubicTo(0.43 * s, 0.19 * s, 0.30 * s, 0.36 * s, 0.31 * s, 0.56 * s)
            path.cubicTo(0.32 * s, 0.77 * s, 0.52 * s, 0.88 * s, 0.73 * s, 0.78 * s)
            path.cubicTo(0.52 * s, 0.94 * s, 0.20 * s, 0.82 * s, 0.14 * s, 0.55 * s)
            path.cubicTo(0.08 * s, 0.28 * s, 0.33 * s, 0.05 * s, 0.67 * s, 0.16 * s)
            painter.drawPath(path)
        elif name in {"chevron-down", "chevron-up"}:
            if name == "chevron-down":
                line(0.27, 0.39, 0.5, 0.62)
                line(0.5, 0.62, 0.73, 0.39)
            else:
                line(0.27, 0.61, 0.5, 0.38)
                line(0.5, 0.38, 0.73, 0.61)
        elif name == "minimize":
            line(0.3, 0.75, 0.7, 0.75)
        elif name == "maximize":
            painter.drawRoundedRect(QtCore.QRectF(0.28 * s, 0.26 * s, 0.44 * s, 0.44 * s), 0.06 * s, 0.06 * s)
        elif name == "restore":
            painter.drawRoundedRect(QtCore.QRectF(0.26 * s, 0.38 * s, 0.46 * s, 0.38 * s), 0.06 * s, 0.06 * s)
            painter.drawRoundedRect(QtCore.QRectF(0.28 * s, 0.22 * s, 0.46 * s, 0.38 * s), 0.06 * s, 0.06 * s)
        elif name == "close":
            line(0.3, 0.3, 0.7, 0.7)
            line(0.7, 0.3, 0.3, 0.7)
        else:
            painter.drawEllipse(QtCore.QRectF(0.22 * s, 0.22 * s, 0.56 * s, 0.56 * s))
        painter.end()
        return QtGui.QIcon(pixmap)
