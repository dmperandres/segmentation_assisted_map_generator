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

import globals
import shaders
import math


from copy import deepcopy

POSITION_NORMALIZATION_HOMOGENEOUS = 0

class layer_map_value_segmentation:
    def __init__(self, gl, parent=None):
        # super(layer_map_mhd, self).__init__(parent)
        self.gl = gl
        self.shader_program = None

        # self.context = contextdata.getContext()
        self.VAO = GLuint(0)
        self.tex_input_segments_image = GLuint(0)
        self.tex_output_image = GLuint(0)
        self.buffer_positions_data = GLuint(0)
        self.buffer_valid_positions = GLuint(0)

        self.mode = globals.INTERPOLATION_METHOD_SEGMENT_BASED_MEAN
        self.valid_positions = []
        self.loaded = False
        self.null_value = 255

        self.result_floats_image = []
        self.result_rgba = []

        self.shader_program = None

        self.width = None
        self.height = None



    def load_shaders(self):
        if self.shader_program == None:
            with open('shaders/value_segmentation.vert', 'r') as file:
                VERTEX_SHADER = file.read()

            with open('shaders/value_segmentation.frag', 'r') as file:
                FRAGMENT_SHADER = file.read()

            self.shader_program = shaders.load_program(VERTEX_SHADER, FRAGMENT_SHADER)

            if self.shader_program == 0:
                print("Error with shaders mhd_segmentation")
                sys.exit(1)

            # create the VAO
            glCreateVertexArrays(1, self.VAO)

    def create_buffers(self):
        glBindVertexArray(self.VAO)

        # for the segments image
        glCreateTextures(GL_TEXTURE_2D, 1, self.tex_input_segments_image)
        glTextureStorage2D(self.tex_input_segments_image, 1, GL_R8, self.width, self.height);  # RGBA
        glTextureSubImage2D(self.tex_input_segments_image, 0, 0, 0, self.width, self.height, GL_RED, GL_UNSIGNED_BYTE,
                            self.segments_image)

        # for the result image
        glCreateTextures(GL_TEXTURE_2D, 1, self.tex_output_image)
        glTextureStorage2D(self.tex_output_image, 1, GL_R32F, self.width,
                           self.height);  # R

        # The buffer for the positions data (x, y, value, color, segment_id).It will be a SSB
        glGenBuffers(1, self.buffer_positions_data)
        glBindBuffer(GL_SHADER_STORAGE_BUFFER, self.buffer_positions_data);
        glBufferData(GL_SHADER_STORAGE_BUFFER, self.positions_data.nbytes, self.positions_data, GL_STATIC_DRAW)

        # The buffer for the color of the input data.It will be a SSB
        # glGenBuffers(1, self.buffer_colors)
        # glBindBuffer(GL_SHADER_STORAGE_BUFFER, self.buffer_colors)
        # glBufferData(GL_SHADER_STORAGE_BUFFER, self.colors.nbytes, self.colors, GL_STATIC_DRAW)

        # The buffer for the valid positions
        glGenBuffers(1, self.buffer_valid_positions)
        glBindBuffer(GL_SHADER_STORAGE_BUFFER, self.buffer_valid_positions)
        glBufferData(GL_SHADER_STORAGE_BUFFER, self.valid_positions.nbytes, self.valid_positions, GL_STATIC_DRAW);

        glBindVertexArray(0)

    def set_data(self, segments_image, positions_data, valid_positions, lut, mode, null_value):
        self.computed = False
        self.segments_image = segments_image
        self.positions_data = positions_data
        self.valid_positions = valid_positions
        self.width = self.segments_image.shape[1]
        self.height = self.segments_image.shape[0]
        self.lut = lut
        self.mode = mode
        self.null_value = null_value

    def get_result_float_image(self):
        return self.result_floats_image

    def get_result_rgba_image(self):
        return self.result_rgba

    def update_layer(self):
        self.gl.makeCurrent()
        if self.loaded == False:
            self.loaded = True
            self.load_shaders()

        self.create_buffers()

        glUseProgram(self.shader_program)
        glBindVertexArray(self.VAO)
        glUseProgram(self.shader_program);
        glBindImageTexture(0, self.tex_input_segments_image, 0, GL_FALSE, 0, GL_READ_ONLY, GL_R8)
        glBindImageTexture(1, self.tex_output_image, 0, GL_FALSE, 0, GL_WRITE_ONLY, GL_R32F)

        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, self.buffer_positions_data)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 1, self.buffer_valid_positions)

        glUniform1i(0, int(self.width))
        glUniform1i(1, int(self.height))
        glUniform1i(2, int(len(self.positions_data)))

        # mode
        # glUniform1i(3, int(self.probe))
        glUniform1i(3, int(self.mode))
        # null value
        glUniform1i(4, int(self.null_value))

        #
        glViewport(0, 0, self.width, self.height)
        # draw a point for each pixel
        glDrawArrays(GL_POINTS, 0, self.width*self.height)

        # read the result
        if len(self.result_floats_image) == 0:
            self.result_floats_image = np.empty((self.height, self.width), dtype=np.float32)

        glBindTexture(GL_TEXTURE_2D, self.tex_output_image)
        glGetTexImage(GL_TEXTURE_2D, 0, GL_RED, GL_FLOAT, self.result_floats_image)

        glBindVertexArray(0)
        glUseProgram(0)

        glDeleteTextures(1, self.tex_input_segments_image)
        glDeleteTextures(1, self.tex_output_image)
        glDeleteBuffers(1, self.buffer_positions_data)
        glDeleteBuffers(1, self.buffer_valid_positions)

        #
        # glDeleteProgram(self.shader_program)
        # glDeleteVertexArrays(1, self.VAO)

        self.result_rgba = self.apply_colormap(self.result_floats_image, self.lut)
        # self.apply_color_mixing()

    def apply_colormap(self, float_image, lut):
        image_aux = deepcopy(float_image)
        image_aux = image_aux*255.0
        image_aux = image_aux.astype(np.uint8)
        result_gray = cv2.cvtColor(image_aux,cv2.COLOR_GRAY2RGB,3)
        result = cv2.LUT(result_gray, lut)
        return cv2.cvtColor(result,cv2.COLOR_RGB2RGBA, 4)

    # def apply_color_mixing(self):
    #     pass
