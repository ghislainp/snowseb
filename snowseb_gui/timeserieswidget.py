#!/usr/bin/python

import matplotlib.dates as mdates
import datetime
import pytz
import bisect

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import pyqtSignal, QTimer
from .timeserieswidget_gui5 import Ui_Form


class TimeSeriesWidget(QWidget):

    plot = pyqtSignal(int)

    def __init__(self, parent=None, dts=[]):

        QWidget.__init__(self, parent)

        # Configure l'interface utilisateur

        self.ui = Ui_Form()
        self.ui.setupUi(self)

        self.ui.forward_time.clicked.connect(
            lambda: self.move_button_clicked(+1))
        self.ui.backward_time.clicked.connect(
            lambda: self.move_button_clicked(-1))
        self.ui.fastforward_time.clicked.connect(
            lambda: self.move_button_clicked(+12))
        self.ui.fastbackward_time.clicked.connect(
            lambda: self.move_button_clicked(-12))
        self.ui.play.toggled.connect(self.play)

        self.ui.start_time.clicked.connect(self.to_begin)
        self.ui.end_time.clicked.connect(self.to_end)

        self.connect_datetime_edit(True)

        self.speed = 1
        self.timeresolution = 24  # hourly

        self.set_datetime_list(dts)
        self.to_begin()

    def set_datetime_list(self, dts):
        self.dts = dts
        self.playing = False

        if len(dts) == 1:
            firstdate = lastdate = dts[0]
        elif len(dts) >= 2:
            firstdate, lastdate = dts[0], dts[-1]

            self.connect_datetime_edit(False)
            self.ui.horizontalSlider.setRange(mdates.date2num(
                firstdate) * self.timeresolution, mdates.date2num(lastdate) * self.timeresolution)
            self.connect_datetime_edit(True)
            self.ui.datetime_edit.setDate(firstdate)

    def extend_datetime_list(self, newdts):
        dts = list(set(self.dts) + set(newdts))
        dts.sort()
        self.set_datetime_list(dts)

    def set_timeresolution(self, dtres):
        self.timeresolution = dtres

    def connect_datetime_edit(self, state):
        if state:
            self.ui.datetime_edit.dateTimeChanged.connect(
                self.to_date_from_edit)
            self.ui.horizontalSlider.valueChanged.connect(
                self.to_date_from_slider)
        else:
            self.ui.datetime_edit.dateTimeChanged.disconnect(
                self.to_date_from_edit)
            self.ui.horizontalSlider.valueChanged.disconnect(
                self.to_date_from_slider)

    def move_button_clicked(self, speed_or_inc):
        self.speed = speed_or_inc
        if self.playing:
            self.goto_next_record(speed_or_inc)
        else:
            self.goto_next_record(speed_or_inc)

    def to_begin(self):
        self.current = 0
        if len(self.dts) > self.current:
            self.set_date(self.dts[self.current])
            self.plot.emit(self.current)

    def to_end(self):
        self.current = len(self.dts)-1
        self.set_date(self.dts[self.current])
        self.plot.emit(self.current)

    def to_date(self, dt):

        # search dt after dt based on speed
        if self.speed < 0:
            self.current = bisect.bisect_left(self.dts, dt)
        else:
            self.current = bisect.bisect_right(self.dts, dt)

        # i+=self.speed
        if self.current < 0:
            self.current = 0
        if self.current >= len(self.dts):
            self.current = len(self.dts) - 1

        # if self.current<0 or self.current >= len(self.dts):
        #    self.stop_playing()
        #    return

        self.set_date(self.dts[self.current])
        self.plot.emit(self.current)

    def to_date_from_edit(self):
        dt = qtdatetime2datetime(self.ui.datetime_edit.dateTime())
        self.to_date(dt)

    def to_date_from_slider(self, i):
        dt = mdates.num2date(float(i)/self.timeresolution)
        self.to_date(dt)

    def set_date(self, dt):
        if dt is not None:
            self.connect_datetime_edit(False)
            self.ui.datetime_edit.setDateTime(dt)
            self.ui.horizontalSlider.setValue(
                mdates.date2num(dt)*self.timeresolution)
            self.connect_datetime_edit(True)

    def play(self, state):
        if state:  # play
            self.playing = True
            self.timer = QTimer()
            self.timer.timeout.connect(self.goto_next_record)
            self.timer.start(100)
        else:  # pause
            self.stop_playing()

    def stop_playing(self):
        if self.playing:
            self.playing = False
            del self.timer
            self.ui.play.setChecked(False)

    def goto_next_record(self, inc=None):

        if self.playing or inc is None:
            inc = self.speed

        if self.current is None:
            self.current = 0
        else:
            self.current += inc

        if self.current < 0 or self.current >= len(self.dts):
            self.stop_playing()
            return

        self.set_date(self.dts[self.current])
        self.plot.emit(self.current)


def qtdatetime2datetime(qtdatetime):
    d = qtdatetime.date()
    t = qtdatetime.time()
    return datetime.datetime(d.year(), d.month(), d.day(), t.hour(), t.minute(), t.second(), tzinfo=pytz.UTC)


if __name__ == "__main__":

    import sys
    from numpy import arange

    app = QApplication(sys.argv)

    dts = mdates.num2date(arange(700000, 800000))

    win = TimeSeriesWidget(dts=dts)

    def printla(s):
        print(s)
    win.plot.connect(printla)

    win.show()
    sys.exit(app.exec_())
