import pathlib
from PyQt5.QtCore import Qt

import yaml

from .model import Point, ClockStyle


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
        if not config['draggable']:
            self._flag.append(Qt.WindowTransparentForInput)

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
        self._flag.toggle(Qt.WindowTransparentForInput)
        self._reloadRequired = True
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
