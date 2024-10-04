import sys
from PySide6.QtCore import Qt, Slot, QDir, QSize, Signal
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtGui import QMatrix4x4, QAction, QPixmap, QIcon, QFontMetrics, QFont
from PySide6.QtWidgets import (
    QWidget,
    QMainWindow,
    QApplication,
    QFileDialog,
    QStyle,
    QColorDialog,
    QHBoxLayout,
    QVBoxLayout,
    QGridLayout,
    QTabWidget,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QCheckBox,
    QRadioButton,
    QGroupBox,
    QSlider,
    QSpinBox,
    QMessageBox,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QFrame,
    QSizePolicy,
    QProgressDialog,
)

import os
import numpy as np
import cv2
import glob
from OpenGL.GL import *

import gl_widget
import layer_map_mhd
import project_data
import globals
import color_table
import button_color

from dataclasses import dataclass, field
from typing import List



# layer_type, layer_name, element_name, visible, transparency, inversion, texture
# @dataclass
# class mhd_parameters:
#     color1 : bool = True
#     color2 : bool = True
#     color3 : bool = True
#     position1 : bool = True
#     position2 : bool = True

class interpolation_parameters_widget(QFrame):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.mhd_parameters_values = [True]*5

        self.interpolation_method = globals.INTERPOLATION_METHOD_DEFAULT
        self.value_normalization = globals.VALUE_NORMALIZATION_DEFAULT
        self.position_normalization = globals.POSITION_NORMALIZATION_DEFAULT
        self.probe_size = globals.PROBE_SIZES[globals.PROBE_SIZE_DEFAULT]

        self.setFrameStyle(QFrame.Panel)
        self.gridlayout = QGridLayout()

        pos = 0

        label_interpolation_method = QLabel('Interpolation method')
        combobox_interpolation_method = QComboBox()
        combobox_interpolation_method.addItems(globals.INTERPOLATION_METHODS_TEXT)
        combobox_interpolation_method.setCurrentIndex(globals.INTERPOLATION_METHOD_DEFAULT)
        combobox_interpolation_method.currentIndexChanged.connect(self.interpolation_method_changed)

        self.gridlayout.addWidget(label_interpolation_method, pos, 0)
        self.gridlayout.addWidget(combobox_interpolation_method, pos, 1)
        pos += 1

        text_labels = ['Color 1', 'Color 2', 'Color 3', 'Position 1', 'Position 2']
        self.list_checkbox = []

        for i in range(len(text_labels)):
            checkbox = QCheckBox()
            checkbox.setChecked(True)
            checkbox.clicked.connect(self.mhd_parameters_changed)
            self.list_checkbox.append(checkbox)
            self.gridlayout.addWidget(QLabel(text_labels[i]), pos, 0)
            self.gridlayout.addWidget(self.list_checkbox[i], pos, 1)
            pos += 1

        label_value_normalization = QLabel('Value normalization')
        checkbox_value_normalization = QCheckBox()
        if globals.VALUE_NORMALIZATION_DEFAULT == True:
            checkbox_value_normalization.setChecked(True)
        checkbox_value_normalization.clicked.connect(self.value_normalization_changed)
        self.gridlayout.addWidget(label_value_normalization, pos, 0)
        self.gridlayout.addWidget(checkbox_value_normalization, pos, 1)
        pos += 1

        label_position_normalization = QLabel( 'Position normalization')
        checkbox_position_normalization = QCheckBox()
        if globals.POSITION_NORMALIZATION_DEFAULT == True:
            checkbox_position_normalization.setChecked(True)
        checkbox_position_normalization.clicked.connect(self.position_normalization_changed)
        self.gridlayout.addWidget(label_position_normalization, pos, 0)
        self.gridlayout.addWidget(checkbox_position_normalization, pos, 1)
        pos += 1

        label_probe_size = QLabel('Probe size')
        combobox_probe_size = QComboBox()
        combobox_probe_size.addItems(globals.PROBE_SIZES_TEXT)
        combobox_probe_size.setCurrentIndex(globals.PROBE_SIZE_DEFAULT)
        combobox_probe_size.currentIndexChanged.connect(self.probe_size_changed)

        self.gridlayout.addWidget(label_probe_size, pos, 0)
        self.gridlayout.addWidget(combobox_probe_size, pos, 1)
        pos += 1

        self.setLayout(self.gridlayout)

    @Slot()
    def interpolation_method_changed(self, index):
        self.interpolation_method = index

    @Slot()
    def mhd_parameters_changed(self):
        valid = False
        for pos in range(len(self.list_checkbox)):
            if self.list_checkbox[pos].isChecked():
                valid = True
                break

        checkbox = self.sender()
        if valid == True:
            pos = self.list_checkbox.index(checkbox)
            if checkbox.isChecked():
                self.mhd_parameters_values[pos] = True
            else:
                self.mhd_parameters_values[pos] = False
        else:
            checkbox.blockSignals(True)
            checkbox.setChecked(True)
            checkbox.blockSignals(False)

    @Slot()
    def position_normalization_changed(self):
        checkbox = self.sender()
        if checkbox.isChecked():
            self.position_normalization = True
        else:
            self.position_normalization = False

    @Slot()
    def value_normalization_changed(self):
        checkbox = self.sender()
        if checkbox.isChecked():
            self.value_normalization = True
        else:
            self.value_normalization = False

    @Slot()
    def probe_size_changed(self, index):
        self.probe_size = globals.PROBE_SIZES[index]


    def get_parameters(self):
        return self.interpolation_method, self.mhd_parameters_values, self.position_normalization, self.value_normalization, self.probe_size
