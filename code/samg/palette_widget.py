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
# class layer:
#     layer_type : int
#     layer_name: str
#     element_name : str
#     visible : bool
#     transparency : float
#     inversion : bool
#     texture : GLuint

class palette_widget(QFrame):
    def __init__(self, colormap_names, parent = None):
        super().__init__(parent)

        self.setFrameStyle(QFrame.Panel)
        self.gridlayout = QGridLayout()

        label_palette_type = QLabel('Palette type')
        combobox_palette_type = QComboBox()
        text = [str(value) for value in color_table.PALETTE_TYPE_TEXT]
        combobox_palette_type.addItems(text)
        combobox_palette_type.setCurrentIndex(color_table.PALETTE_TYPE_DEFAULT)
        combobox_palette_type.currentIndexChanged.connect(self.palette_type_changed)
        self.palette_type = color_table.PALETTE_TYPE_DEFAULT

        label_color_type = QLabel('Color type')
        combobox_color_type = QComboBox()
        text = [str(value) for value in color_table.PALETTE_COLOR_TYPE_TEXT]
        combobox_color_type.addItems(text)
        combobox_color_type.setCurrentIndex(color_table.PALETTE_COLOR_TYPE_DEFAULT)
        combobox_color_type.currentIndexChanged.connect(self.color_type_changed)
        self.color_type = color_table.PALETTE_COLOR_TYPE_DEFAULT

        label_intervals = QLabel('Intervals')
        self.spinbox_intervals = QSpinBox()
        if color_table.PALETTE_TYPE_DEFAULT == color_table.PALETTE_TYPE_DISCRETE:
            self.num_intervals = 2
            self.spinbox_intervals.setMinimum(2)
        else:
            self.num_intervals = 1
            self.spinbox_intervals.setMinimum(1)
        self.spinbox_intervals.setMaximum(10)
        self.spinbox_intervals.valueChanged.connect(self.intervals_changed)

        label_zero_color = QLabel('0 color')
        combobox_zero_color = QComboBox()
        text = [str(value) for value in color_table.PALETTE_ZERO_COLOR_TEXT]
        combobox_zero_color.addItems(text)
        combobox_zero_color.currentIndexChanged.connect(self.zero_color_changed)
        self.zero_color = color_table.PALETTE_ZERO_COLOR_DEFAULT

        label_color_assigning = QLabel('Color assigning')
        combobox_color_assigning = QComboBox()
        text = [str(value) for value in color_table.PALETTE_COLOR_ASSIGNING_TEXT]
        combobox_color_assigning.addItems(text)
        combobox_color_assigning.setCurrentIndex(color_table.PALETTE_COLOR_ASSIGNING_DEFAULT)
        combobox_color_assigning.currentIndexChanged.connect(self.color_assigning_changed)
        self.color_assigning = color_table.PALETTE_COLOR_ASSIGNING_DEFAULT

        label_fixed_color = QLabel('Color')
        buttoncolor_fixed_color = button_color.button_color(Qt.red)
        buttoncolor_fixed_color.colorChanged.connect(self.color_changed)
        self.color = np.array([1, 0, 0])

        label_colormap_names = QLabel('Color map')
        combobox_colormap_names = QComboBox()
        self.colormap_names = [value for value in colormap_names]
        self.colormap_names.sort()
        combobox_colormap_names.addItems(self.colormap_names)
        combobox_colormap_names.currentIndexChanged.connect(self.colormap_names_changed)
        self.colormap_name = self.colormap_names[0]

        self.gridlayout.addWidget(label_palette_type, 0, 0)
        self.gridlayout.addWidget(combobox_palette_type, 0, 1)
        self.gridlayout.addWidget(label_color_type, 1, 0)
        self.gridlayout.addWidget(combobox_color_type, 1, 1)
        self.gridlayout.addWidget(label_intervals, 2, 0)
        self.gridlayout.addWidget(self.spinbox_intervals, 2, 1)
        self.gridlayout.addWidget(label_zero_color, 3, 0)
        self.gridlayout.addWidget(combobox_zero_color, 3, 1)
        self.gridlayout.addWidget(label_color_assigning, 4, 0)
        self.gridlayout.addWidget(combobox_color_assigning, 4, 1)
        self.gridlayout.addWidget(label_fixed_color, 5, 0)
        self.gridlayout.addWidget(buttoncolor_fixed_color, 5, 1)
        self.gridlayout.addWidget(label_colormap_names, 6, 0)
        self.gridlayout.addWidget(combobox_colormap_names, 6, 1)

        self.setLayout(self.gridlayout)

        # if self.palette_type == color_table.PALETTE_TYPE_DISCRETE:
        if  self.color_type == color_table.PALETTE_COLOR_TYPE_SINGLE:
            if self.color_assigning == color_table.PALETTE_COLOR_ASSIGNING_RANDOM:
                self.change_row_visibility(self.gridlayout, 5, False)
                self.change_row_visibility(self.gridlayout, 6, False)
            else:
                self.change_row_visibility(self.gridlayout, 5, True)
                self.change_row_visibility(self.gridlayout, 6, False)
        else: # multiple
            self.change_row_visibility(self.gridlayout, 5, False)
            self.change_row_visibility(self.gridlayout, 6, True)


    def update_grid(self):
        if  self.color_type == color_table.PALETTE_COLOR_TYPE_SINGLE:
            self.change_row_visibility(self.gridlayout, 3, True)
            self.change_row_visibility(self.gridlayout, 4, True)
            if self.color_assigning == color_table.PALETTE_COLOR_ASSIGNING_RANDOM:
                self.change_row_visibility(self.gridlayout, 5, False)
                self.change_row_visibility(self.gridlayout, 6, False)
            else:
                self.change_row_visibility(self.gridlayout, 5, True)
                self.change_row_visibility(self.gridlayout, 6, False)
        else: # multiple
            self.change_row_visibility(self.gridlayout, 3, False)
            self.change_row_visibility(self.gridlayout, 4, False)
            self.change_row_visibility(self.gridlayout, 5, False)
            self.change_row_visibility(self.gridlayout, 6, True)

    @Slot()
    def palette_type_changed(self, index):
        self.palette_type = index
        if self.palette_type == color_table.PALETTE_TYPE_DISCRETE:
            if self.num_intervals == 1:
                self.num_intervals = 2
                self.spinbox_intervals.blockSignals(True)
                self.spinbox_intervals.setValue(self.num_intervals)
                self.spinbox_intervals.blockSignals(False)

        self.update_grid()

    @Slot()
    def color_type_changed(self, index):
        self.color_type = index
        self.update_grid()

    @Slot()
    def intervals_changed(self, value):
        if self.palette_type == color_table.PALETTE_TYPE_DISCRETE:
            if value == 1:
                value = 2
                self.spinbox_intervals.blockSignals(True)
                self.spinbox_intervals.setValue(value)
                self.spinbox_intervals.blockSignals(False)
        self.num_intervals = value

    @Slot()
    def zero_color_changed(self, index):
        self.zero_color = index

    @Slot()
    def color_assigning_changed(self, index):
        self.color_assigning = index
        self.update_grid()

    @Slot()
    def color_changed(self, color):
        # self.color = np.array([color.red(), color.green(), color.blue(), 255]).astype(np.uint8)
        self.color = [color.red()//255, color.green()//255, color.blue()//255]

    @Slot()
    def colormap_names_changed(self, index):
        self.colormap_name = self.colormap_names[index]

    def change_row_visibility(self, gridlayout, row, show):
        for i in range(gridlayout.columnCount()):
            item = gridlayout.itemAtPosition(row, i)
            if item != None:
                widget = item.widget()
                if widget != None:
                    if show == True:
                        widget.show()
                    else:
                        widget.hide()

    def get_palette_parameters(self):
        palette = color_table.palette()
        palette.type = self.palette_type
        palette.color_type = self.color_type
        palette.intervals = self.num_intervals
        if self.zero_color == 0:
            palette.start_color = color_table.BLACK
        else:
            palette.start_color = color_table.WHITE
        palette.color_assigning = self.color_assigning
        palette.end_color = self.color
        palette.colormap_name = self.colormap_name
        return palette
