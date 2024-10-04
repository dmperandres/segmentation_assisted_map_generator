import math
import random
import sys
from PySide6.QtCore import Qt, Slot, QDir, QSize, Signal, QRect, QRectF
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtGui import (QMatrix4x4, QAction, QPixmap, QIcon, QFontMetrics, QFont, QColor, QPainter, QLinearGradient,
                            QPainterPath)

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

class colorbar(QWidget):
    def __init__(self, max_value, height, font, painter = None, scale = 1, square_size = globals.COLORBAR_SQUARE_SIZE,
                 margin = globals.COLORBAR_MARGIN,
                 space = globals.COLORBAR_SPACE):
        super().__init__()

        self.palette = color_table.palette
        self.palette.intervals = 0 # to draw nothing

        self.color_table = color_table.color_table()

        self.setMinimumHeight(200)

        self.visibility = False
        # self.values = []
        self.max_value = max_value
        # self.intervals = 0
        self.square_size = square_size
        self.margin = margin
        self.space = space

        self.element_name = ''

        self.painter = painter

        self.scale = scale

        self.font_aux = font

        self.update_widget_size(height)

    def update_widget_size(self, height):
        # Calcular el ancho requerido basado en el texto más grande (valor máximo)
        logarithm = int(math.log10(self.max_value))
        self.num_decimals = 7 - logarithm
        if self.num_decimals < 0:
            self.num_decimals = 0

        max_value_text = f"{self.max_value:.{self.num_decimals}f}"
        font1 = QFont(self.font_aux)
        font1.setPointSize(self.font_aux.pointSize() * self.scale)
        font_metrics = QFontMetrics(font1)
        text_width = font_metrics.horizontalAdvance(max_value_text)

        # Calcular el ancho necesario para el widget
        self.widget_width = 3 * self.square_size * self.scale + 2 * self.space + text_width  # Añadir un poco más de margen

        self.setMinimumWidth(self.widget_width)
        # self.setMaximumWidth(self.widget_width)

        self.setMinimumHeight(height)
        # self.setMaximumHeight(height)

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)


    def set_max_value(self, max_value):
        self.max_value = max_value

    def get_width(self):
        return self.widget_width

    def set_visibility(self, visibility):
        self.visibility = visibility
        self.update()

    def set_parameters(self, element_name, max_value, palette):
        self.element_name = element_name
        self.max_value = max_value
        self.palette = palette
        self.intervals = self.palette.intervals
        if self.painter == None:
            self.update()
        else:
            self.draw()

    def paintEvent(self, event):
        if self.palette.type == color_table.PALETTE_TYPE_DISCRETE:
            if self.palette.color_type == color_table.PALETTE_COLOR_TYPE_SINGLE:
                self.compute_parameters_discrete_single()
            else:
                self.compute_parameters_discrete_multiple()
        else:
            if self.palette.color_type == color_table.PALETTE_COLOR_TYPE_SINGLE:
                self.compute_parameters_continuous_single()
            else:
                self.compute_parameters_continuous_multiple()

    def draw(self):
        if self.palette.type == color_table.PALETTE_TYPE_DISCRETE:
            if self.palette.color_type == color_table.PALETTE_COLOR_TYPE_SINGLE:
                self.compute_parameters_discrete_single()
            else:
                self.compute_parameters_discrete_multiple()
        else:
            if self.palette.color_type == color_table.PALETTE_COLOR_TYPE_SINGLE:
                self.compute_parameters_continuous_single()
            else:
                self.compute_parameters_continuous_multiple()


    def compute_parameters_discrete_single(self):
        if self.visibility == True:
            self.colors = []
            self.values = []
            self.computed_values = []
            for i in range(self.intervals+1):
                t = float(i)/ float(self.intervals)
                start_color = QColor(self.palette.start_color[0]*255.0, self.palette.start_color[1]*255.0,
                                     self.palette.start_color[2]*255.0)
                end_color = QColor(self.palette.end_color[0]*255.0, self.palette.end_color[1]*255.0,
                                     self.palette.end_color[2]*255.0)
                self.colors.append(self.interpolate_color(t, start_color, end_color))
                self.values.append(t)
                self.computed_values.append(self.max_value * t)
            # copy the last color to the previous position
            self.colors[len(self.colors)-2] = self.colors[len(self.colors)-1]
            self.draw_sections()

    def compute_parameters_discrete_multiple(self):
        if self.visibility == True:
            self.colors = []
            self.values = []
            self.computed_values = []
            for i in range(self.intervals+1):
                t = float(i)/ float(self.intervals)
                pos = int(t*255.0)
                color = self.color_table.colormaps[self.palette.colormap_name][pos,0]
                self.colors.append(QColor(color[0], color[1], color[2]))
                self.values.append(t)
                self.computed_values.append(self.max_value * t)
            self.draw_sections()

    def compute_parameters_continuous_single(self):
        if self.visibility == True:
            self.colors = []
            self.values = []
            self.computed_values = []
            for i in range(self.intervals+1):
                t = float(i)/ float(self.intervals)
                start_color = QColor(self.palette.start_color[0]*255.0, self.palette.start_color[1]*255.0,
                                     self.palette.start_color[2]*255.0)
                end_color = QColor(self.palette.end_color[0]*255.0, self.palette.end_color[1]*255.0,
                                   self.palette.end_color[2]*255.0)
                self.colors.append(self.interpolate_color(t, start_color, end_color))
                self.values.append(t)
                self.computed_values.append(self.max_value * t)
            self.draw_continuous()

    def compute_parameters_continuous_multiple(self):
        if self.visibility == True:
            self.colors = []
            self.values = []
            self.computed_values = []
            for i in range(self.intervals+1):
                t = float(i)/ float(self.intervals)
                pos = int(t*255.0)
                color = self.color_table.colormaps[self.palette.colormap_name][pos]
                self.colors.append(QColor(color[0,0], color[0,1], color[0,2]))
                self.values.append(t)
                self.computed_values.append(self.max_value * t)
            self.draw_continuous()

    def draw_sections(self):
        if self.painter == None:
            painter = QPainter(self)
            new_painter = True
        else:
            new_painter = False
            painter = self.painter

        # Obtener el tamaño del widget sin los margenes
        widget_width = self.widget_width - globals.COLORBAR_MARGIN
        widget_height = self.height() - globals.COLORBAR_MARGIN

        font = painter.font()
        normal_font_size = font.pointSize() * self.scale
        big_font_size = normal_font_size * 2

        big_font = QFont()
        big_font.setPointSize(big_font_size)

        # obtener la altura del texto para poder ajustar donde comienzan las cajas y la barra
        normal_font = QFont()
        normal_font.setPointSize(normal_font_size)

        metrics = QFontMetrics(normal_font)
        # Obtener el rectángulo que contiene al texto
        normal_font_height = metrics.tightBoundingRect('123456789').height()

        # obtener el espacio vertical para el texto y la barra
        text_height = normal_font_height * 2.5  # 0.5 more
        bar_height = widget_height - text_height

        # Dibujar el texto 'Pb' en la parte superior
        painter.setFont(big_font)
        text = self.element_name
        text_rect = painter.boundingRect(globals.COLORBAR_MARGIN, 0, widget_width, big_font_size, Qt.AlignCenter, text)
        painter.drawText(text_rect, Qt.AlignCenter, text)

        # Calcular la posición inicial del rectángulo y otros elementos debajo del texto 'Pb'
        top_margin = text_rect.bottom() + self.margin * self.scale

        rect_height = (widget_height - top_margin - self.margin * self.scale) / (len(self.colors)-1)
        for pos in range(len(self.colors)-1):
            pos_square = len(self.colors) - 2 - pos
            # rect = QRectF(self.square_size + self.space, top_margin + pos_square * rect_height, self.square_size,
            #               rect_height)
            rect = QRectF((self.square_size + self.space) * self.scale, top_margin + pos_square * rect_height,
                          self.square_size * self.scale, rect_height)
            painter.fillRect(rect, self.colors[pos])
            painter.drawRect(rect)

        # use last color
        painter.fillRect(rect, self.colors[pos])
        painter.drawRect(rect)

        # Dibujar los pequeños cuadrados con los colores inicial y final en las posiciones correspondientes
        painter.setFont(normal_font)  # Restablecer la fuente normal para los valores
        for pos in range(len(self.values)-1):
            value = self.values[pos]
            # y_pos = top_margin + value * (widget_height - top_margin - margin)
            # y_pos = widget_height - self.margin - value * (widget_height - top_margin - self.margin)
            y_pos = widget_height - self.margin * self.scale - value * (
                    widget_height - top_margin - self.margin * self.scale)
            # color = self.interpolate_color(value)
            # rect = QRectF(0, y_pos - self.square_size, self.square_size, self.square_size)
            rect = QRectF(0, y_pos - self.square_size * self.scale // 2, self.square_size * self.scale,
                          self.square_size * self.scale)
            painter.fillRect(rect, self.colors[pos])
            painter.drawRect(rect)

        # text
        for pos in range(len(self.values)):
            value = self.values[pos]
            # y_pos = top_margin + value * (widget_height - top_margin - margin)
            # y_pos = widget_height - self.margin - value * (widget_height - top_margin - self.margin)
            y_pos = widget_height - self.margin * self.scale - value * (
                widget_height - top_margin - self.margin * self.scale)
            # Dibujar la línea horizontal
            start_x = self.square_size * self.scale
            end_x = (self.square_size + self.space + self.square_size + self.space) * self.scale
            painter.drawLine(start_x, y_pos, end_x, y_pos)

            # Dibujar el valor del texto
            computed_value = self.computed_values[pos]
            painter.drawText(end_x + 5, y_pos + normal_font_height//2, f"{computed_value:.{self.num_decimals}f}")

        if new_painter == True:
            painter.end()

    def draw_continuous(self):
        if self.painter == None:
            painter = QPainter(self)
            new_painter = True
        else:
            new_painter = False
            painter = self.painter

        # Obtener el tamaño del widget sin los margenes
        widget_width = self.widget_width - globals.COLORBAR_MARGIN
        widget_height = self.height() - globals.COLORBAR_MARGIN

        font = painter.font()
        normal_font_size = font.pointSize() * self.scale
        big_font_size = normal_font_size * 2

        big_font = QFont()
        big_font.setPointSize(big_font_size)

        # obtener la altura del texto para poder ajustar donde comienzan las cajas y la barra
        normal_font = QFont()
        normal_font.setPointSize(normal_font_size)

        metrics = QFontMetrics(normal_font)
        # Obtener el rectángulo que contiene al texto
        normal_font_height = metrics.tightBoundingRect('123456789').height()

        # obtener el espacio vertical para el texto y la barra
        text_height = normal_font_height * 2.5 # 0.5 more
        bar_height = widget_height - text_height


        # Dibujar el texto 'Pb' en la parte superior
        painter.setFont(big_font)
        text = self.element_name
        text_rect = painter.boundingRect(globals.COLORBAR_MARGIN, 0, widget_width, big_font_size, Qt.AlignCenter, text)
        painter.drawText(text_rect, Qt.AlignCenter, text)

        # Calcular la posición inicial del rectángulo y otros elementos debajo del texto 'Pb'
        top_margin = text_rect.bottom() + self.margin * self.scale

        # Definir el gradiente lineal
        gradient = QLinearGradient(0, top_margin, 0, widget_height - self.margin * self.scale)
        if self.palette.color_type == color_table.PALETTE_COLOR_TYPE_SINGLE:
            gradient.setColorAt(1, self.colors[0])
            gradient.setColorAt(0, self.colors[len(self.colors)-1])
        else:
            for i in range(256):
                t = float(i) / 255.0
                color_np = self.color_table.colormaps[self.palette.colormap_name][i]
                color = QColor(color_np[0,0], color_np[0,1], color_np[0,2])
                gradient.setColorAt(1 - t , color)

        # Dibujar el rectángulo con el gradiente
        # rect = QRectF(margin, top_margin, widget_width // 2 - margin, widget_height - top_margin - margin)
        rect = QRectF((self.square_size + self.space) * self.scale, top_margin, self.square_size * self.scale,
                      widget_height - top_margin - self.margin * self.scale)
        painter.fillRect(rect, gradient)
        painter.drawRect(rect)

        # Dibujar los pequeños cuadrados con los colores inicial y final en las posiciones correspondientes
        painter.setFont(normal_font)  # Restablecer la fuente normal para los valores
        for pos in range(len(self.values)):
            value = self.values[pos]
            # y_pos = top_margin + value * (widget_height - top_margin - margin)
            y_pos = widget_height - self.margin * self.scale - value * (widget_height - top_margin - self.margin * self.scale) - 1
            if self.palette.color_type == color_table.PALETTE_COLOR_TYPE_SINGLE:
                color = self.interpolate_color(value, self.colors[0], self.colors[len(self.colors)-1])
            else:
                color = self.colors[pos]

            rect = QRectF(0, y_pos - self.square_size * self.scale // 2, self.square_size * self.scale,
                          self.square_size * self.scale)
            painter.fillRect(rect, color)
            painter.drawRect(rect)

            # Dibujar la línea horizontal
            start_x = self.square_size * self.scale
            end_x = (self.square_size + self.space + self.square_size + self.space) * self.scale
            painter.drawLine(start_x, y_pos, end_x, y_pos)

            # Dibujar el valor del texto
            computed_value = self.computed_values[pos]
            painter.drawText(end_x + 5, y_pos + normal_font_height//2, f"{computed_value:.{self.num_decimals}f}")

        if new_painter == True:
            painter.end()

    def interpolate_color(self, value, color1, color2):
        r = color1.red() + value * (color2.red() - color1.red())
        g = color1.green() + value * (color2.green() - color1.green())
        b = color1.blue() + value * (color2.blue() - color1.blue())
        return QColor(int(r), int(g), int(b))
