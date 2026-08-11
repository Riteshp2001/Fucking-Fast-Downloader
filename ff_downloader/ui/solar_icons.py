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
        pen = QtGui.QPen(QtGui.QColor(color), max(1.6, size / 12), QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.NoBrush)
        s = float(size)

        def line(x1, y1, x2, y2):
            painter.drawLine(QtCore.QPointF(x1 * s, y1 * s), QtCore.QPointF(x2 * s, y2 * s))

        if name == "paste":
            painter.drawRoundedRect(QtCore.QRectF(.25*s, .22*s, .5*s, .6*s), .1*s, .1*s)
            painter.drawRoundedRect(QtCore.QRectF(.37*s, .11*s, .26*s, .18*s), .06*s, .06*s)
            line(.36,.48,.64,.48); line(.36,.62,.58,.62)
        elif name == "shield":
            path = QtGui.QPainterPath(QtCore.QPointF(.5*s,.1*s)); path.lineTo(.78*s,.22*s); path.lineTo(.74*s,.58*s); path.quadTo(.68*s,.79*s,.5*s,.9*s); path.quadTo(.32*s,.79*s,.26*s,.58*s); path.lineTo(.22*s,.22*s); path.closeSubpath(); painter.drawPath(path)
            line(.37,.5,.47,.61); line(.47,.61,.66,.4)
        elif name == "copy":
            painter.drawRoundedRect(QtCore.QRectF(.3*s,.28*s,.48*s,.5*s), .09*s,.09*s)
            painter.drawRoundedRect(QtCore.QRectF(.18*s,.16*s,.48*s,.5*s), .09*s,.09*s)
        elif name == "download":
            line(.5,.15,.5,.6); line(.32,.44,.5,.62); line(.68,.44,.5,.62)
            painter.drawRoundedRect(QtCore.QRectF(.2*s,.67*s,.6*s,.18*s), .08*s,.08*s)
        elif name == "folder":
            path = QtGui.QPainterPath(QtCore.QPointF(.15*s,.3*s)); path.lineTo(.37*s,.3*s); path.lineTo(.45*s,.2*s); path.lineTo(.78*s,.2*s); path.quadTo(.86*s,.2*s,.86*s,.3*s); path.lineTo(.86*s,.72*s); path.quadTo(.86*s,.82*s,.76*s,.82*s); path.lineTo(.24*s,.82*s); path.quadTo(.14*s,.82*s,.14*s,.72*s); path.closeSubpath(); painter.drawPath(path)
        elif name == "pause":
            line(.37,.25,.37,.75); line(.63,.25,.63,.75)
        elif name == "play":
            path = QtGui.QPainterPath(QtCore.QPointF(.38*s,.25*s)); path.lineTo(.72*s,.5*s); path.lineTo(.38*s,.75*s); path.closeSubpath(); painter.drawPath(path)
        elif name == "stop":
            painter.drawRoundedRect(QtCore.QRectF(.28*s,.28*s,.44*s,.44*s), .08*s,.08*s)
        elif name == "link":
            painter.drawRoundedRect(QtCore.QRectF(.13*s,.36*s,.42*s,.24*s), .11*s,.11*s)
            painter.drawRoundedRect(QtCore.QRectF(.45*s,.36*s,.42*s,.24*s), .11*s,.11*s)
            line(.4,.48,.6,.48)
        elif name == "activity":
            line(.12,.55,.3,.55); line(.3,.55,.4,.32); line(.4,.32,.55,.7); line(.55,.7,.68,.45); line(.68,.45,.88,.45)
        else:
            painter.drawEllipse(QtCore.QRectF(.22*s,.22*s,.56*s,.56*s))
        painter.end()
        return QtGui.QIcon(pixmap)
