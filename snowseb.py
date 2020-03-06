#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#    SnowSEB
#    Copyright (C) 2013-2020 Ghislain Picard
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.


import csv

from PyQt5.QtWidgets import QMainWindow, QApplication, QFileDialog
import time
import matplotlib.dates as mdates

import numpy as np
import codecs


def model(variables, parameters):

    simul = dict()
    tair, rh, windspeed = variables['Tair'], variables['RH'], variables['WindSpeed']
    swdn, swup, lwdn, lwup = variables['SWdn'], variables['SWup'], variables['LWdn'], variables['LWup']
    if 'P' in variables:
        pressure = variables['P']
    else:
        pressure = parameters['P']

    z0, zt = parameters['z0'], parameters['zt']

    # constant
    # fusion heat (J/kg)
    lambdaf = 3.335e5
    # sublimation heat (J/kg)
    lambdas = 2.838e6
    # air density (kg/m3)
    rhoair = pressure / (287.0 * tair)
    # air specific heat capacity [J/KG-K]
    cpair = 1005.0
    # boltzmann constant [W/m^2-K^4]
    sigma = 5.669E-8
    # snow emissivity in the thermal infrared
    epsilon = 1.00

    # compute net shortwave
    net_shortwave = swdn + swup

    # compute net longwave
    net_longwave = lwdn + lwup

    # estimate surface temperature
    # inverse: lwup = epsilon*sigma*ts**4
    ts = (abs(lwup) / (epsilon * sigma))**0.25
    # ts[ts>273.15]=273.15
    simul['Ts'] = ts

    # turbulent fluxes
    von_karman = 0.4
    chn = von_karman**2 / (np.log(zt / z0))**2

    # conductance
    fn = 1  # neutral condition#
    ga = chn * fn * windspeed

    # sensible flux
    sensible = rhoair * cpair * ga * (tair - ts)

    # latent flux
    eps = 0.622
    psatair = vaporsaturation_liquid(tair)
    qair = rh * psatair / (pressure - (1 - eps) * rh * psatair)
    simul['Qair'] = qair

    psatsurf = vaporsaturation_ice(ts)
    # print 'ratio ice/liquid',vaporsaturation_ice(ts)/vaporsaturation_liquid(ts)
    qsatsurf = eps * psatsurf / (pressure - (1 - eps) * psatsurf)
    simul['Qsatsurf'] = qsatsurf
    # print rh,qair,qsatsurf

    latent = lambdas * rhoair * ga * (qair - qsatsurf)

    # bilan complet
    G = - (net_shortwave + net_longwave + sensible + latent)

    simul['L'] = latent
    simul['H'] = sensible
    simul['G'] = G

    return simul


# goff-gracht over water below0 C
# http://cires.colorado.edu/~voemel/vp.html
def vaporsaturation_liquid(T):

    log10ew = -7.90298 * (373.16 / T - 1) + 5.02808 * np.log10(373.16 / T) \
        - 1.3816e-7 * (10**(11.344 * (1 - T / 373.16)) - 1) \
        + 8.1328e-3 * (10**(-3.49149 * (373.16 / T - 1)) - 1) \
        + np.log10(1013.246)

    return 100 * 10**log10ew


# Goff Gratch equation over ice
# http://cires.colorado.edu/~voemel/vp.html
def vaporsaturation_ice(T):

    log10ei = -9.09718 * (273.16 / T - 1) \
        - 3.56654 * np.log10(273.16 / T) \
        + 0.876793 * (1 - T / 273.16) \
        + np.log10(6.1071)

    return 100 * 10**log10ei


def read_campbell_file(filename, mapping=None):

    f = codecs.open(filename, 'r', encoding='iso-8859-1')
    lines = f.readlines()

    # lines=open(filename,'rb').readlines()

    headerlines = 4
    nline = 0
    n = len(lines) - headerlines

    data = dict()
    csvreader = csv.reader(lines, delimiter=',', quotechar='"')
    row = next(csvreader)  # skip the first line
    nline += 1

    row = next(csvreader)
    nline += 1
    if row[0] != "TIMESTAMP":
        n -= 1
        row = next(csvreader)
        nline += 1

    headerrow = row

    next(csvreader)  # skip the third line # unit
    next(csvreader)  # skip the fourth line # process

    count = 0
    for row in csvreader:
        nline += 1
        if not row:  # skip empty lines
            continue

        for i, fieldname in enumerate(headerrow):
            if mapping:
                if fieldname not in mapping:
                    continue
                fieldname = mapping[fieldname]

            if not fieldname in data:
                data[fieldname] = np.zeros(n)
            try:
                x = row[i]
                if x == 'NAN':
                    x = nan
                elif i == 0:
                    x = mdates.datestr2num(x)
                else:
                    x = float(x)

                data[fieldname][count] = x
            except:
                raise Exception("Erreur line %i" % nline)

        count += 1

    # resize if necessary
    for k in data:
        if isinstance(data[k], np.ndarray):
            data[k] = data[k][0:count]

    return data


# Main class
class EnergyGui(QMainWindow):

    def __init__(self, filename=None):
        QMainWindow.__init__(self)

        # Configure l'interface utilisateur
        from snowseb_gui.energy_gui5 import Ui_MainWindow
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # vilain mais c'est plus simple comme ca
        self.ui.mplwidget.figure.delaxes(self.ui.mplwidget.axes)
        self.ui.mplwidget.figure.set_facecolor('w')

        self.axes1 = self.ui.mplwidget.figure.add_subplot(211)
        self.axes2 = self.ui.mplwidget.figure.add_subplot(212)
        self.canvas = self.ui.mplwidget.canvas

        self.simul = dict()
        self.ui.timeseries_widget.plot.connect(self.plot_budget)

        self.vars = ['SWdn', 'SWup', 'SWnet',
                     'LWdn', 'LWup', 'LWnet', 'H', 'L', 'G']
        self.colors = ['#FF6600', '#FFCC99', '#FFFF00', 'red',
                       '#FF6699', '#EC799A', '#339900', '#3399FF', 'gray']

        if filename is not None:
            self.import_campbell(filename)

        self.ui.z0_spinbox.valueChanged.connect(self.replot)
        self.ui.zt_spinbox.valueChanged.connect(self.replot)
        self.ui.pressure_spinbox.valueChanged.connect(self.replot)

        self.ui.actionImport_file.triggered.connect(self.import_file)

    def import_file(self):
        filename = QFileDialog.getOpenFileName(
            self, "Open File", "", "*.csv, *.dat")
        filename = filename[0]
        if filename == "":
            return
        self.import_campbell(filename)

    def import_campbell(self, filename):

        mapping = {'TIMESTAMP': 'date', 'SUp_Avg': 'SWup', 'SDn_Avg': 'SWdn',
                   'LUpCo_Avg': 'LWup', 'LDnCo_Avg': 'LWdn',
                   'AirTC_Avg': 'Tair', 'WS_ms_S_WVT': 'WindSpeed', 'RH': 'RH'}

        self.data = read_campbell_file(filename, mapping)
        self.data['Tair'] += 273.15
        self.data['RH'] *= 0.01
        self.data['LWup'] *= -1
        self.data['SWup'] *= -1

        self.dts = mdates.num2date(self.data['date'])
        self.ui.timeseries_widget.set_datetime_list(self.dts)

        self.run_model()

        self.set_axis_limit()
        self.plot_timeseries()
        self.plot_budget(0)

    def set_axis_limit(self):
        ma = -1e9
        mi = 1e9

        for var in self.vars:
            if var in self.data:
                ma = max(ma, max(self.data[var]))
                mi = min(mi, min(self.data[var]))
            if var in self.simul:
                ma = max(ma, max(self.simul[var]))
                mi = min(mi, min(self.simul[var]))

        self.y_max = min(ma + 50, 1300)  # evite les blow up
        self.y_min = max(mi - 50, -1300)

    def replot(self):
        if hasattr(self, "data"):
            self.plot_timeseries()
            self.plot_budget(self.ui.timeseries_widget.current)

    def plot_timeseries(self):
        for var, c in zip(self.vars, self.colors):
            if var in self.data:
                self.axes1.plot_date(self.dts, self.data[var], '-', color=c)
            if var in self.simul:
                self.axes1.plot_date(self.dts, self.simul[var], '--', color=c)

        self.axes1.xaxis.set_major_formatter(
            mdates.DateFormatter('%Y-%m-%d\n%H:%M'))
        self.axes1.xaxis.set_major_locator(mdates.AutoDateLocator())
        self.axes1.set_ylabel("W m$^{-2}$")

    def plot_budget(self, i=None):

        ind = np.arange(len(self.vars))
        width = 0.35 * 2

        self.axes2.clear()

        offset = 0.4

        self.axes2.plot([min(ind) + offset, max(ind) + offset],
                        [0, 0], color='k', alpha=0.4)

        j = 0
        for var in self.vars:
            if var in self.data:
                self.axes2.bar(j + offset, self.data[var][i],
                               width, color=self.colors[j])
            elif var in self.simul:
                self.axes2.bar(j + offset, self.simul[var][i],
                               width, color=self.colors[j], hatch='//')
            elif var in ['SWnet', 'LWnet']:
                dn = self.data[var[0:2] + 'dn']
                up = self.data[var[0:2] + 'up']
                self.axes2.bar(j + offset, dn[i] + up[i], width,
                               color=self.colors[j], hatch='o')

                # y.append(self.simul[var][i])
                # hatch.append('//')
            # else:
            #    y.append(0)
            #    hatch.append('.')

            j += 1

        # self.axes2.bar(ind+width,ys,width,color=self.colors,hatch='//')

        # self.axes2.set_xlim((-0.1,len(self.vars)-1+2*width+0.1))
        self.axes2.set_xlim((-0.1, len(self.vars) - 1 + 2 * width + 0.1))
        self.axes2.set_xticks(ind + width / 2)
        self.axes2.set_xticklabels(self.vars)
        self.axes2.set_ylabel("W m$^{-2}$")

        if not hasattr(self, "y_min"):
            self.set_axis_limit()
        self.axes1.set_ylim((self.y_min, self.y_max))
        self.axes2.set_ylim((self.y_min, self.y_max))

        self.canvas.draw()

        # print information
        self.ui.tair_label.setText(u"%5.1f °C" %
                                   (self.data['Tair'][i] - 273.15))
        if 'Ts' in self.simul:
            self.ui.ts_label.setText(u"%5.1f °C" %
                                     (self.simul['Ts'][i] - 273.15))
        else:
            self.ui.ts_label.setText("--")

        self.ui.rh_label.setText("%5i %%" % int(self.data['RH'][i] * 100))
        if 'Qair' in self.simul:
            self.ui.qair_label.setText("%5.1f g/kg" %
                                       (self.simul['Qair'][i] * 1000))
        else:
            self.ui.qair_label.setText("--")
        if 'Qsatsurf' in self.simul:
            self.ui.qsatsurf_label.setText(
                "%5.1f g/kg" % (self.simul['Qsatsurf'][i] * 1000))
        else:
            self.ui.qsatsurf_label.setText("--")
        self.ui.windspeed_label.setText(
            "%5.1f m/s" % self.data['WindSpeed'][i])

    def launch_compute(self):
        QTimer.singleShot(20, self.compute)


#    def compute(self,i0=0):
#
#        parameters=dict()
#        parameters['z0']=self.ui.z0_spinbox.value()
#        parameters['albedo']=self.ui.albedo_spinbox.value()
#
#        parameters['zt']=self.ui.zt_spinbox.value()
#
#        if not hasattr(self,"model"):
#            model = Model()
#
#        t0 = time.time()
#        for i in range(i0,len(data['Tair'])):
#            d={ k: data[k][i] for k in data}
#
#            res = model.solve(d,parameters)
#
#            if i==0:
#                self.simul={ k: empty_like(data['Tair']) for k in res }
#
#            for k in res:
#                self.simul[k][i]=res[k]
#
#            if i % 10 ==0 and time.time()-t0>=2:
#                QTimer.singleShot(10,lambda: self.compute(i+1))
#        return

    def run_model(self):

        parameters = dict()
        parameters['z0'] = self.ui.z0_spinbox.value()
        parameters['zt'] = self.ui.zt_spinbox.value()
        parameters['P'] = self.ui.pressure_spinbox.value()

        self.simul = model(self.data, parameters)


if __name__ == "__main__":

    import sys
    app = QApplication(sys.argv)
    w = EnergyGui()

    w.show()
    sys.exit(app.exec_())
