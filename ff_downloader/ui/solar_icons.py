from __future__ import annotations

from functools import lru_cache

from PyQt5 import QtCore, QtGui, QtSvg


class SolarIconFactory:
    """Render a small embedded subset of the real Solar linear icon set.

    Solar Icons are designed by 480 Design and distributed under CC BY 4.0.
    The SVG path data below comes from the Solar collection published by Iconify.
    Embedding only the glyphs used by the UI keeps packaged builds lightweight.
    """

    _BODIES = {
        "download": (
            '<g fill="none" stroke="currentColor" stroke-linecap="round" '
            'stroke-linejoin="round" stroke-width="1.5"><path d="M3 15c0 2.828 0 '
            '4.243.879 5.121C4.757 21 6.172 21 9 21h6c2.828 0 4.243 0 '
            '5.121-.879C21 19.243 21 17.828 21 15"/><path d="M12 3v13m-4-4.375L12 '
            '16l4-4.375"/></g>'
        ),
        "paste": (
            '<g fill="none" stroke="currentColor" stroke-width="1.5"><path d="M16 '
            '4.002c2.175.012 3.353.109 4.121.877C21 5.758 21 7.172 21 10v6c0 '
            '2.829 0 4.243-.879 5.122C19.243 22 17.828 22 15 22H9c-2.828 0-4.243 '
            '0-5.121-.878C3 20.242 3 18.829 3 16v-6c0-2.828 0-4.242.879-5.121.768'
            '-.768 1.946-.865 4.121-.877"/><path stroke-linecap="round" d="M7 14.5h8M7 '
            '18h5.5"/><path d="M8 3.5A1.5 1.5 0 0 1 9.5 2h5A1.5 1.5 0 0 1 16 '
            '3.5v1A1.5 1.5 0 0 1 14.5 6h-5A1.5 1.5 0 0 1 8 4.5z"/></g>'
        ),
        "copy": (
            '<g fill="none" stroke="currentColor" stroke-width="1.5"><path d="M6 '
            '11c0-2.828 0-4.243.879-5.121C7.757 5 9.172 5 12 5h3c2.828 0 4.243 0 '
            '5.121.879C21 6.757 21 8.172 21 11v5c0 2.828 0 4.243-.879 5.121C19.243 '
            '22 17.828 22 15 22h-3c-2.828 0-4.243 0-5.121-.879C6 20.243 6 18.828 '
            '6 16z"/><path d="M6 19a3 3 0 0 1-3-3v-6c0-3.771 0-5.657 1.172-6.828S7.229 '
            '2 11 2h4a3 3 0 0 1 3 3"/></g>'
        ),
        "folder": (
            '<g fill="none" stroke="currentColor" stroke-width="1.5"><path '
            'stroke-linecap="round" d="M18 10h-5"/><path d="M2 6.95c0-.883 0-1.324.07-1.692A4 '
            '4 0 0 1 5.257 2.07C5.626 2 6.068 2 6.95 2c.386 0 .58 0 .766.017a4 4 0 '
            '0 1 2.18.904c.144.119.28.255.554.529L11 4c.816.816 1.224 1.224 1.712 '
            '1.495a4 4 0 0 0 .848.352C14.098 6 14.675 6 15.828 6h.374c2.632 0 '
            '3.949 0 4.804.77q.119.105.224.224c.77.855.77 2.172.77 4.804V14c0 3.771 '
            '0 5.657-1.172 6.828S17.771 22 14 22h-4c-3.771 0-5.657 0-6.828-1.172S2 '
            '17.771 2 14z"/></g>'
        ),
        "pause": (
            '<path fill="none" stroke="currentColor" stroke-width="1.5" d="M2 '
            '6c0-1.886 0-2.828.586-3.414S4.114 2 6 2s2.828 0 3.414.586S10 4.114 10 '
            '6v12c0 1.886 0 2.828-.586 3.414S7.886 22 6 22s-2.828 0-3.414-.586S2 '
            '19.886 2 18zm12 0c0-1.886 0-2.828.586-3.414S16.114 2 18 2s2.828 0 '
            '3.414.586S22 4.114 22 6v12c0 1.886 0 2.828-.586 3.414S19.886 22 18 '
            '22s-2.828 0-3.414-.586S14 19.886 14 18z"/>'
        ),
        "play": (
            '<path fill="none" stroke="currentColor" stroke-width="1.5" '
            'd="M20.409 9.353a2.998 2.998 0 0 1 0 5.294L7.597 21.614C5.534 22.737 3 '
            '21.277 3 18.968V5.033c0-2.31 2.534-3.769 4.597-2.648z"/>'
        ),
        "stop": (
            '<path fill="none" stroke="currentColor" stroke-width="1.5" d="M2 '
            '12c0-4.714 0-7.071 1.464-8.536C4.93 2 7.286 2 12 2s7.071 0 8.535 '
            '1.464C22 4.93 22 7.286 22 12s0 7.071-1.465 8.535C19.072 22 16.714 22 '
            '12 22s-7.071 0-8.536-1.465C2 19.072 2 16.714 2 12Z"/>'
        ),
        "link": (
            '<g fill="none" stroke="currentColor" stroke-linecap="round" '
            'stroke-width="1.5"><path d="m12.792 15.8 1.43-1.432a6.076 6.076 0 0 0 '
            '0-8.59 6.067 6.067 0 0 0-8.583 0L2.778 8.643A6.076 6.076 0 0 0 6.732 '
            '19"/><path d="m11.208 8.2-1.43 1.432a6.076 6.076 0 0 0 0 8.59 6.067 6.067 '
            '0 0 0 8.583 0l2.861-2.864A6.076 6.076 0 0 0 17.268 5"/></g>'
        ),
        "document": (
            '<g fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 '
            '10c0-3.771 0-5.657 1.172-6.828S7.229 2 11 2h2c3.771 0 5.657 0 6.828 '
            '1.172S21 6.229 21 10v4c0 3.771 0 5.657-1.172 6.828S16.771 22 13 22h-2c'
            '-3.771 0-5.657 0-6.828-1.172S3 17.771 3 14z"/><path stroke-linecap="round" '
            'd="M8 12h8M8 8h8m-8 8h5"/></g>'
        ),
        "sun": (
            '<g fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" '
            'cy="12" r="5"/><path stroke-linecap="round" d="M12 2v2m0 16v2M4 12H2m20 '
            '0h-2m-.222-7.777-2.222 2.031M4.222 4.223l2.222 2.031m0 11.302-2.222 '
            '2.222m15.556-.001-2.222-2.222"/></g>'
        ),
        "moon": (
            '<path fill="none" stroke="currentColor" stroke-linejoin="round" '
            'stroke-width="1.5" d="M12 22c5.523 0 10-4.477 10-10 0-.463-.694-.54-.933-.143a6.5 '
            '6.5 0 1 1-8.924-8.924C12.54 2.693 12.463 2 12 2 6.477 2 2 6.477 2 '
            '12s4.477 10 10 10Z"/>'
        ),
        "minimize": (
            '<path fill="none" stroke="currentColor" stroke-linecap="round" '
            'stroke-width="1.75" d="M6 12h12"/>'
        ),
        "maximize": (
            '<rect x="5.5" y="5.5" width="13" height="13" rx="1" fill="none" '
            'stroke="currentColor" stroke-width="1.6"/>'
        ),
        "restore": (
            '<g fill="none" stroke="currentColor" stroke-linejoin="round" stroke-width="1.6">'
            '<path d="M8 5.5h10.5V16"/><path d="M16 8H5.5v10.5H16z"/></g>'
        ),
        "close": (
            '<path fill="none" stroke="currentColor" stroke-linecap="round" '
            'stroke-width="1.75" d="m7 7 10 10m0-10L7 17"/>'
        ),
    }

    @classmethod
    @lru_cache(maxsize=128)
    def icon(cls, name: str, color: str = "#D8DEE9", size: int = 20) -> QtGui.QIcon:
        body = cls._BODIES.get(name, cls._BODIES["link"])
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" '
            f'viewBox="0 0 24 24">{body.replace("currentColor", color)}</svg>'
        )
        renderer = QtSvg.QSvgRenderer(QtCore.QByteArray(svg.encode("utf-8")))
        pixmap = QtGui.QPixmap(size, size)
        pixmap.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        return QtGui.QIcon(pixmap)
