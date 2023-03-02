pyuic5 -x energy_gui.ui | sed -e 's/from matplotlibwidget/from snowseb_gui.matplotlibwidget/' -e 's/from timeserieswidget/from snowseb_gui.timeserieswidget/'  >energy_gui5.py
pyuic5 -x  timeserieswidget_gui.ui > timeserieswidget_gui5.py
