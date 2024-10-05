import pathlib
import sys
import time
from datetime import datetime
from typing import Callable

from PyQt5 import QtCore
from PyQt5.QtCore import QPoint, Qt, QTimer
from PyQt5.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import (QAction, QApplication, QDialog, QGroupBox, QLabel,
                             QMenu, QSizePolicy, QSystemTrayIcon, QVBoxLayout,
                             QWidget, qApp)

from .outlinedlabel import OutlinedLabel
from .model import Point, ClockStyle
from .setting import Setting

MODULE_DIR = pathlib.Path(__file__).parent


class DigitalClock(QWidget):
    INTERVAL = 500  # ms

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)
        self.setLayout(layout)

        self.label = OutlinedLabel('00:00')
        self.label.setScaledOutlineMode(False)
        self.label.setOutlineThickness(5)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        layout.addWidget(self.label)

        self._initTimer()

    def _initTimer(self):
        timer = QTimer(self)
        timer.timeout.connect(self._onTimeout)
        timer.start(self.INTERVAL)

    def _onTimeout(self):
        now = datetime.now().strftime('%H:%M')
        self.label.setText(now)

    def setClockStyle(self, style: ClockStyle):
        self.setStyleSheet(f'''
            font-size: {style.size}px;
            text-align: center;
            font-weight: bold;
            color: {style.color};
        ''')


class ClockWidget(QWidget):
    DRAGGING_STYLE = 'border: 3px dashed blue'

    def __init__(self, settings: Setting):
        super().__init__()
        self._settings = settings

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)
        self.setLayout(layout)

        self.clock = DigitalClock()
        self.clock.setClockStyle(self._settings.clockStyle)
        layout.addWidget(self.clock)

        self.setWindowFlags(self._settings.windowFlag)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(self.clock.sizeHint())

        pos = self._settings.position
        if pos.x is not None and pos.y is not None:
            self.move(pos.x, pos.y)

    def reload(self):
        if self._settings.reloadRequired:
            self.setWindowFlags(self._settings.windowFlag)
            time.sleep(1)  # sleepを入れないと安定してWindowFlagを更新できない (>= 1s)
            self.show()

            self._settings.reloaded()

    def mousePressEvent(self, event):
        self.oldPos = event.globalPos()
        self.setStyleSheet(self.DRAGGING_STYLE)

    def mouseMoveEvent(self, event):
        delta = QPoint(event.globalPos() - self.oldPos)
        if self._settings.draggable:
            self.move(self.x() + delta.x(), self.y() + delta.y())
        self.oldPos = event.globalPos()

    def mouseReleaseEvent(self, event):
        self.setStyleSheet('')
        point = Point(self.x(), self.y())
        self._settings.savePosition(point)

    def enterEvent(self, event):
        if self._settings.hidable:
            self.clock.hide()

    def leaveEvent(self, event):
        if self._settings.hidable:
            self.clock.show()


class TrayIcon(QSystemTrayIcon):
    def __init__(self, settings: Setting):
        super().__init__()
        self._settings = settings

        iconPath = MODULE_DIR.joinpath('icon.png')
        self.setIcon(QIcon(str(iconPath)))

        self._trayIconMenu = QMenu()
        self.setContextMenu(self._trayIconMenu)

        self._widget = ClockWidget(settings)
        self._initMenu()
        self._widget.show()

    def _initMenu(self):
        self._registerAction('Open Clock', self._widget.show)
        self._registerAction('Close Clock', self._widget.close)
        self._trayIconMenu.addSeparator()
        self._registerAction('Toggle Always Show Top', self._settings.toggleAlwaysShowTop)
        self._registerAction('Toggle Draggable', self._settings.toggleDraggable)
        self._trayIconMenu.addSeparator()
        self._registerAction("Quit", qApp.quit)

    def _registerAction(self, label: str, callback: Callable):
        q_action = QAction(label, self)

        def _callback():
            callback()
            self._widget.reload()

        q_action.triggered.connect(_callback)
        self._trayIconMenu.addAction(q_action)


def main():
    app = QApplication(sys.argv)
    iconPath = MODULE_DIR.joinpath('icon.png')
    app.setWindowIcon(QIcon(str(iconPath)))
    QApplication.setQuitOnLastWindowClosed(False)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        raise OSError("We could't detect any system tray on this system.")

    config_path = pathlib.Path().home().joinpath('.config', 'nattoujam', 'nattou-clock', 'config.yml')
    settings = Setting(config_path)
    trayIcon = TrayIcon(settings)
    trayIcon.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
