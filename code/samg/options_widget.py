import math
import random
import sys
from PySide6.QtCore import Qt, Slot, QDir, QSize, Signal, QRect, QRectF
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtGui import (QMatrix4x4, QAction, QPixmap, QIcon, QFontMetrics, QFont, QColor, QPainter, QLinearGradient,
                            QPainterPath, QPen)

from PySide6.QtWidgets import (
    QWidget,
    QDialog,
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
    QDialogButtonBox,
)

import os
import numpy as np
import cv2
import glob
from OpenGL.GL import *
import colorsys
import copy

import gl_widget
import layer_map_mhd
import project_data
import globals
import color_table

from dataclasses import dataclass, field
from typing import Any


# @dataclass
# class palette:
#     type : int = PALETTE_TYPE_DEFAULT
#     color_type: int = PALETTE_COLOR_TYPE_DEFAULT
#     intervals : int = 1
#     zero_color : int = 0
#     color_assigning : int = PALETTE_COLOR_ASSIGNING_DEFAULT
#     color : np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=int))
#     colormap_name : str = 'jet'

class color_square(QWidget):
    def __init__(self, size, color, parent=None):
        super().__init__(parent)
        self.color = QColor(color[0], color[1], color[2])
        self.color_np = [self.color.red(), self.color.green(), self.color.blue(), 255]
        self.setFixedSize(size, size)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.color)
        painter.setPen(QPen(Qt.black, 1))
        rect = self.rect().adjusted(1, 1, -1, -1)  # Ajustar para el borde
        painter.drawRect(rect)  # Dibuja el borde

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            color = QColorDialog.getColor(self.color, self)
            if color.isValid():
                self.color = color
                self.color_np = [self.color.red(), self.color.green(), self.color.blue(), 255]
                self.update()

class display_tab(QWidget):
    def __init__(self, font_size, out_circle_size, font_color, out_circle_color, in_circle_color,
                 selection_out_circle_color, parent=None):
        super().__init__(parent)
        gridlayout = QGridLayout()

        label_font_size = QLabel('Font size')
        self.spinbox_font_size = QSpinBox(self)
        self.spinbox_font_size.setValue(font_size)

        label_out_circle_size = QLabel('Out circle size')
        self.spinbox_out_circle_size = QSpinBox(self)
        self.spinbox_out_circle_size.setValue(out_circle_size)

        label_font_color = QLabel('Font color')
        self.color_square_font = color_square(20, font_color)

        label_out_circle_color = QLabel('Out circle color')
        self.color_square_out_circle = color_square(20, out_circle_color)

        label_in_circle_color = QLabel('In circle color')
        self.color_square_in_circle = color_square(20, in_circle_color)

        label_selection_out_circle_color = QLabel('Selection out circle color')
        self.color_square_selection_out_circle = color_square(20, selection_out_circle_color)

        gridlayout.addWidget(label_font_size, 0, 0, alignment=Qt.AlignRight)
        gridlayout.addWidget(self.spinbox_font_size, 0, 1, alignment=Qt.AlignLeft)
        gridlayout.addWidget(label_out_circle_size, 1, 0, alignment=Qt.AlignRight)
        gridlayout.addWidget(self.spinbox_out_circle_size, 1, 1, alignment=Qt.AlignLeft)
        gridlayout.addWidget(label_font_color, 2, 0, alignment=Qt.AlignRight)
        gridlayout.addWidget(self.color_square_font, 2, 1, alignment=Qt.AlignLeft)
        gridlayout.addWidget(label_out_circle_color, 3, 0, alignment=Qt.AlignRight)
        gridlayout.addWidget(self.color_square_out_circle, 3, 1, alignment=Qt.AlignLeft)
        gridlayout.addWidget(label_in_circle_color, 4, 0, alignment=Qt.AlignRight)
        gridlayout.addWidget(self.color_square_in_circle, 4, 1, alignment=Qt.AlignLeft)
        gridlayout.addWidget(label_selection_out_circle_color, 5, 0, alignment=Qt.AlignRight)
        gridlayout.addWidget(self.color_square_selection_out_circle, 5, 1, alignment=Qt.AlignLeft)

        self.setLayout(gridlayout)


class print_Tab(QWidget):
    def __init__(self, font_scale, parent=None):
        super().__init__(parent)
        gridlayout = QGridLayout()

        label_font_scale = QLabel('Font scale')
        self.spinbox_font_scale = QSpinBox(self)
        self.spinbox_font_scale.setValue(font_scale)
        self.spinbox_font_scale.setRange(1,10)

        gridlayout.addWidget(label_font_scale, 0, 0, alignment=Qt.AlignRight)
        gridlayout.addWidget(self.spinbox_font_scale, 0, 1, alignment=Qt.AlignLeft)

        self.setLayout(gridlayout)

    def update_label(self, value):
        self.label.setText(f"Value: {value}")

class options_widget(QDialog):
    def __init__(self, parent):
        super().__init__(parent)

        self.parent = parent

        values = self.parent.get_options_values()
        # font_size, out_circle_size, font_color, out_circle_color, in_color_size, font_scale
        self.position_font_size = values[0]
        self.position_out_circle_size = values[1]
        self.position_font_color = values[2]
        self.position_out_circle_color = values[3]
        self.position_in_circle_color = values[4]
        self.position_selection_out_circle_color = values[5]
        self.position_font_scale = values[6]

        self.setWindowTitle("Options")
        self.setMinimumWidth(500)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        self.tabs = QTabWidget()

        self.display_tab = display_tab(self.position_font_size, self.position_out_circle_size, self.position_font_color,
                                       self.position_out_circle_color, self.position_in_circle_color,
                                       self.position_selection_out_circle_color)
        self.print_tab = print_Tab(self.position_font_scale)

        self.tabs.addTab(self.display_tab, "Display")
        self.tabs.addTab(self.print_tab, "Print")

        # Crear los botones personalizados
        self.apply_button = QPushButton("Apply")
        self.cancel_button = QPushButton("Close")

        self.apply_button.clicked.connect(self.apply_values)
        self.cancel_button.clicked.connect(self.end)

        self.button_box = QDialogButtonBox()
        self.button_box.addButton(self.apply_button, QDialogButtonBox.AcceptRole)
        self.button_box.addButton(self.cancel_button, QDialogButtonBox.RejectRole)

        layout = QVBoxLayout()
        layout.addWidget(self.tabs)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

    def apply_values(self):
        font_size = self.display_tab.spinbox_font_size.value()
        out_circle_size = self.display_tab.spinbox_out_circle_size.value()
        font_color = self.display_tab.color_square_font.color_np
        out_circle_color = self.display_tab.color_square_out_circle.color_np
        in_circle_color = self.display_tab.color_square_in_circle.color_np
        selection_out_circle_color = self.display_tab.color_square_selection_out_circle.color_np
        font_scale = self.print_tab.spinbox_font_scale.value()

        self.parent.set_options_values((font_size, out_circle_size, font_color, out_circle_color, in_circle_color,
                                        selection_out_circle_color, font_scale))

    def end(self):
        font_size = self.display_tab.spinbox_font_size.value()
        out_circle_size = self.display_tab.spinbox_out_circle_size.value()
        font_color = self.display_tab.color_square_font.color_np
        out_circle_color = self.display_tab.color_square_out_circle.color_np
        in_circle_color = self.display_tab.color_square_in_circle.color_np
        selection_out_circle_color = self.display_tab.color_square_selection_out_circle.color_np
        font_scale = self.print_tab.spinbox_font_scale.value()

        self.parent.set_options_values((font_size, out_circle_size, font_color, out_circle_color, in_circle_color,
                                        selection_out_circle_color, font_scale))
        self.close()