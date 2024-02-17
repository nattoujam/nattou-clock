import pathlib
import sys
import time
from collections import namedtuple
from datetime import datetime
from typing import Callable

import yaml
from PyQt5 import QtCore
from PyQt5.QtCore import QPoint, Qt, QTimer
from PyQt5.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import (QAction, QApplication, QDialog, QGroupBox, QLabel,
                             QMenu, QSizePolicy, QSystemTrayIcon, QVBoxLayout,
                             QWidget, qApp)

from .outlinedlabel import OutlinedLabel

MODULE_DIR = pathlib.Path(__file__).parent

Point = namedtuple('Point', ['x', 'y'])
ClockStyle = namedtuple('ClockStyle', ['size', 'color'])


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


class WindowFlag():
    def __init__(self):
        self._currentFlags = list()

    @property
    def raw(self):
        flag = 0
        for f in self._currentFlags:
            flag |= f
        return flag

    def append(self, flag):
        self._currentFlags.append(flag)

    def remove(self, flag):
        self._currentFlags.remove(flag)

    def contain(self, flag) -> bool:
        return flag in self._currentFlags

    def toggle(self, flag):
        if self.contain(flag):
            self.remove(flag)
        else:
            self.append(flag)


class Setting():

    def __init__(self, path: pathlib.Path):
        self._reloadRequired = False
        self._flag = WindowFlag()
        self._flag.append(Qt.FramelessWindowHint)
        self._path = path

        if not path.exists():
            self.initialize()
            path.parent.mkdir(parents=True, exist_ok=True)
            self.dump()

        with open(path, 'r') as f:
            config = yaml.safe_load(f)
            self.initializeFromDict(config)

    def initialize(self):
        self._draggable = False
        self._hidable = False
        self._x = None
        self._y = None
        self._fontSize = 100
        self._fontColor = '#dddddd'
        self._flag.append(Qt.WindowStaysOnTopHint)

    def initializeFromDict(self, config: dict):
        self._draggable = config['draggable']
        self._hidable = config['hidable']
        self._x = config['x']
        self._y = config['y']
        self._fontSize = config['fontSize']
        self._fontColor = config['fontColor']
        if config['alwaysShowTop']:
            self._flag.append(Qt.WindowStaysOnTopHint)

    def dump(self):
        config = dict()
        config['draggable'] = self.draggable
        config['hidable'] = self.hidable
        config['alwaysShowTop'] = self.alwaysShowTop
        config['x'] = self.position.x
        config['y'] = self.position.y
        config['fontSize'] = self.clockStyle.size
        config['fontColor'] = self.clockStyle.color

        with open(self._path, 'w') as f:
            f.write(yaml.dump(config))

    @property
    def draggable(self) -> bool:
        return self._draggable

    def toggleDraggable(self):
        self._draggable = not self._draggable
        self.dump()

    @property
    def hidable(self) -> bool:
        return self._hidable

    def toggleHidable(self):
        self._hidable = not self._hidable
        self.dump()

    @property
    def alwaysShowTop(self) -> bool:
        return self._flag.contain(Qt.WindowStaysOnTopHint)

    def toggleAlwaysShowTop(self):
        self._flag.toggle(Qt.WindowStaysOnTopHint)
        self._reloadRequired = True
        self.dump()

    @property
    def position(self) -> Point:
        return Point(self._x, self._y)

    def savePosition(self, point: Point):
        self._x = point.x
        self._y = point.y
        self.dump()

    @property
    def clockStyle(self) -> ClockStyle:
        return ClockStyle(self._fontSize, self._fontColor)

    def setClockStyle(self, style: ClockStyle):
        self._fontSize = style.size
        self._fontColor = style.color
        self.dump()

    @property
    def reloadRequired(self) -> bool:
        return self._reloadRequired

    def reloaded(self):
        self._reloadRequired = False

    @property
    def windowFlag(self) -> Qt.WindowType:
        return self._flag.raw


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
        self._registerAction('Toggle Hide on Mouseover', self._settings.toggleHidable)
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
