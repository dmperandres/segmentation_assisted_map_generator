import random
import sys
from PySide6.QtCore import Qt, Slot, QDir, QSize, Signal
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtGui import QMatrix4x4, QAction, QPixmap, QIcon, QFontMetrics, QFont, QColor
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

from dataclasses import dataclass, field
from typing import Any

PALETTE_TYPE_DISCRETE = 0
PALETTE_TYPE_CONTINUOUS = 1
PALETTE_TYPE_TEXT =['Discrete', 'Continuous']
PALETTE_TYPE_DEFAULT = PALETTE_TYPE_CONTINUOUS

PALETTE_COLOR_TYPE_SINGLE = 0
PALETTE_COLOR_TYPE_MULTIPLE = 1
PALETTE_COLOR_TYPE_TEXT =['Single', 'Multiple']
PALETTE_COLOR_TYPE_DEFAULT = PALETTE_COLOR_TYPE_SINGLE

PALETTE_COLOR_ASSIGNING_RANDOM = 0
PALETTE_COLOR_ASSIGNING_FIXED = 1
PALETTE_COLOR_ASSIGNING_TEXT =['Random', 'Fixed']
PALETTE_COLOR_ASSIGNING_DEFAULT = PALETTE_COLOR_ASSIGNING_FIXED

WHITE = np.array([1, 1, 1])
BLACK = np.array([0, 0, 0])

PALETTE_ZERO_COLOR = [BLACK, WHITE]
PALETTE_ZERO_COLOR_TEXT = ['Black', 'White']
PALETTE_ZERO_COLOR_DEFAULT = 0

@dataclass
class palette:
    type : int = PALETTE_TYPE_DEFAULT
    color_type: int = PALETTE_COLOR_TYPE_DEFAULT
    intervals : int = 1
    start_color : np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=int))
    color_assigning : int = PALETTE_COLOR_ASSIGNING_DEFAULT
    end_color : np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=int))
    colormap_name : str = 'jet'

class color_table:
    def __init__(self):
        #load de fixed luts
        files = []
        # get a list of files with a extension with full path
        files = glob.glob(os.getcwd()+'/colormaps/*.csv')

        self.colormaps ={}
        for file in files:
            full_name = os.path.basename(file)
            id = os.path.splitext(full_name)[0]
            self.colormaps[id] = self.load_colormap(file)

        # print(self.colormaps['jet'])

    def colormap_names(self):
        return self.colormaps.keys()

    def load_colormap(self, file_name):
        with open(file_name, 'r') as file:
            lines = file.readlines()

            lut = np.zeros((256, 1, 3), dtype=np.uint8)
            pos = 0
            while pos < len(lines) and pos < 256:
                line = lines[pos]
                if len(line)>0:
                    tokens = line.split(';')
                    lut[pos] = [int(float(tokens[0]) * 255.0), int(float(tokens[1]) * 255.0), int(float(tokens[2]) * 255.0)]
                pos += 1

        return lut

    def create_sections_single(self, hue, start_color, num_intervals):
        if num_intervals < 2:
            num_intervals = 2

        color = QColor()

        colors = []
        positions = []
        for i in range(num_intervals):
            t = float(i) / float(num_intervals)

            if np.array_equal(start_color, WHITE):
                color.setHsv(hue, int(t * 255.0), 255)
            else:
                color.setHsv(hue, 255, int(t * 255.0))

            color = color.toRgb()
            color_np = np.array([color.red(), color.green(), color.blue()]).astype(int)
            colors.append(color_np)
            #
            positions.append(int(round(t * 255.0)))
        colors.append(colors[len(colors) - 1])
        positions.append(255)

        lut = np.zeros((256, 1, 3), dtype=np.uint8)
        for i in range(len(positions) - 1):
            for j in range(positions[i], positions[i + 1]):
                lut[j] = colors[i]
        lut[255] = colors[len(colors) - 1]

        return lut


    def create_continous_single(self, hue, start_color, num_intervals):
        if num_intervals < 1:
            num_intervals = 1
        color = QColor()

        colors = []
        positions = []
        for i in range(num_intervals+1):
            t = float(i) / float(num_intervals)

            if np.array_equal(start_color, WHITE):
                color.setHsv(hue, int(t * 255.0), 255)
            else:
                color.setHsv(hue, 255, int(t * 255.0))

            color = color.toRgb()
            color_np = np.array([color.red(), color.green(), color.blue()]).astype(int)
            colors.append(color_np)
            #
            positions.append(int(round(t * 255.0)))

        # colors.append(colors[len(colors) - 1])
        # positions.append(255)

        lut = np.zeros((256, 1, 3), dtype=np.uint8)
        for i in range(len(positions)-1):
            for j in range(positions[i], positions[i + 1]):
                t = float(j) / 255.0
                color1 = (1-t)*colors[i]+t*colors[i+1]
                lut[j] = np.array(color1).astype(np.uint8)
        lut[255] = colors[len(colors) - 1]

        return lut

    def create_sections_multiple(self, num_intervals, fixed_continous_lut):
        # get num_intervals -1 colors from fixed_continuous_lut
        if num_intervals < 2:
            num_intervals = 2

        colors = []
        positions = []
        for i in range(num_intervals):
            t = float(i) / float(num_intervals)
            pos = int(round(255.0 * t))
            colors.append(self.colormaps[fixed_continous_lut][pos])
            #
            positions.append(int(round(t * 255.0)))
        colors.append(colors[len(colors) - 1])
        positions.append(255)

        lut = np.zeros((256, 1, 3), dtype=np.uint8)
        for i in range(len(positions) - 1):
            for j in range(positions[i], positions[i + 1]):
                lut[j] = colors[i]
        lut[255] = colors[len(colors) - 1]

        return lut

    def create_continuous_multiple(self, num_intervals, fixed_continous_lut):
        # get num_intervals -1 colors from fixed_continuous_lut
        if num_intervals < 1:
            num_intervals = 1

        colors = []
        positions = []
        for i in range(num_intervals):
            t = float(i) / float(num_intervals)
            pos = int(round(255.0 * t))
            colors.append(self.colormaps[fixed_continous_lut][pos])
            #
            positions.append(int(round(t * 255.0)))
        colors.append(colors[len(colors) - 1])
        positions.append(255)

        lut = np.zeros((256, 1, 3), dtype=np.uint8)
        for i in range(len(positions) - 1):
            for j in range(positions[i], positions[i + 1]):
                lut[j] = self.colormaps[fixed_continous_lut][j]
        lut[255] = self.colormaps[fixed_continous_lut][len(self.colormaps[fixed_continous_lut]) - 1]

        return lut

    def create(self, palette):
        if palette.type == PALETTE_TYPE_DISCRETE:
            if palette.color_type == PALETTE_COLOR_TYPE_SINGLE:
                if palette.color_assigning == PALETTE_COLOR_ASSIGNING_RANDOM:
                    hue = random.randint(0, 350)
                else: # color fixed
                    color =QColor()
                    color.setRgb(palette.end_color[0], palette.end_color[1], palette.end_color[2])
                    hue = color.hsvHue()
                lut = self.create_sections_single(hue, palette.start_color, palette.intervals)
            else: # multiple
                lut = self.create_sections_multiple(palette.intervals, palette.colormap_name)
        else: # continous
            if palette.color_type == PALETTE_COLOR_TYPE_SINGLE:
                if palette.color_assigning == PALETTE_COLOR_ASSIGNING_RANDOM:
                    hue = random.randint(0, 350)
                else:  # color fixed
                    color = QColor()
                    color.setRgb(palette.end_color[0], palette.end_color[1], palette.end_color[2])
                    hue = color.hsvHue()
                lut = self.create_continous_single(hue, palette.start_color, palette.intervals)
            else:  # multiple
                lut = self.create_continuous_multiple(palette.intervals, palette.colormap_name)

        return lut
