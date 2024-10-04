import math
import sys
from PySide6.QtCore import Qt, Slot, QDir, QSize
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtGui import QMatrix4x4, QAction
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
    QCheckBox,
    QRadioButton,
    QGroupBox,
    QSlider,
    QSpinBox,
    QMessageBox,
    QComboBox,
)
from OpenGL.GL import *
# from OpenGL.GL.shaders import compileProgram, compileShader
import os
import numpy as np
import cv2
import shaders
import globals

def draw_positions(image, coordinates_x, coordinates_y, in_color, out_color, selection_out_color, out_radius,
                   text_height, text_color, draw_positions_number, selected_point,
                   draw_connected_points, connected_points):
    # font
    font = cv2.FONT_HERSHEY_SIMPLEX
    thickness = 3
    font_scale = cv2.getFontScaleFromHeight(font, text_height, thickness)

    M_size, base_line = cv2.getTextSize('M',font,font_scale,thickness)

    if out_radius<8:
        out_radius = 8
    space = int(out_radius / 3 )
    half_radius = int(round((out_radius - space) / 2))
    quarter_radius = int(round(half_radius / 2))
    in_radius = space + int(round(quarter_radius / 2))
    out_radius = in_radius + quarter_radius
    for pos in range(len(coordinates_x)):
        if selected_point == pos:
            cv2.circle(image, (int(coordinates_x[pos]), int(coordinates_y[pos])), out_radius, selection_out_color,
                       quarter_radius, lineType=cv2.LINE_AA)
        else:
            cv2.circle(image, (int(coordinates_x[pos]), int(coordinates_y[pos])), out_radius, out_color,
                       quarter_radius, lineType=cv2.LINE_AA)
        cv2.circle(image, (int(coordinates_x[pos]), int(coordinates_y[pos])), in_radius, in_color, quarter_radius, lineType=cv2.LINE_AA)

        if draw_positions_number == True:
            # coordinates for text
            x_pos = int(coordinates_x[pos])
            y_pos = int(coordinates_y[pos] + out_radius + globals.SPACE_TO_TEXT)
            # get the space ocuppied by the text
            # get the number of digits

            num_digits = int(math.log10(pos + 1)) + 1

            text = str(pos+1)
            # text_size, baseline = cv2.getTextSize(text, font, font_scale, thickness)
            text_size = [num_digits*M_size[0], text_height]
            # check if the text is out of the canvas
            # compute the horizontal displacement
            shift = int(text_size[0] / 2)
            if x_pos - shift > 0: #left
                x_pos = x_pos - shift

            if x_pos+shift + 20 > image.shape[1]:  # right
                x_pos = x_pos - text_size[0] - globals.SPACE_TO_TEXT

            if y_pos + text_size[1] + 10 > image.shape[0]: # top
                # put on the bottom part of the circles
                y_pos = int(coordinates_y[pos] - out_radius - 20 - text_size[1])

            cv2.putText(image, text, (x_pos, y_pos), font, font_scale, text_color, thickness, cv2.LINE_AA,
                        True)

    if draw_connected_points == True:
        for pos in range(len(connected_points)):
            cv2.line(image,[connected_points[pos][0], connected_points[pos][1]],
                     [connected_points[pos][2], connected_points[pos][3]],
                     (0,0,0, 255), 6)
            cv2.line(image, [connected_points[pos][0], connected_points[pos][1]],
                     [connected_points[pos][2], connected_points[pos][3]],
                     (255, 255, 255, 255), 2)

