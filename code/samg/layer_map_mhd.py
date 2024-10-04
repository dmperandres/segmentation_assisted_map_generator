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
import math


from copy import deepcopy

POSITION_NORMALIZATION_HOMOGENEOUS = 0

class layer_map_mhd:
    def __init__(self, gl, parent=None):
        # super(layer_map_mhd, self).__init__(parent)
        self.gl = gl
        self.shader_program = None

        # self.context = contextdata.getContext()
        self.VAO = GLuint(0)
        self.tex_input_normalized_image = GLuint(0)
        self.tex_output_image = GLuint(0)
        self.buffer_positions_data = GLuint(0)
        self.buffer_colors = GLuint(0)
        self.buffer_valid_positions = GLuint(0)

        self.use_colors = np.array([True, True, True])
        self.use_positions = np.array([True, True])
        self.probe = 1
        self.valid_positions = []
        self.position_normalization_type = POSITION_NORMALIZATION_HOMOGENEOUS
        self.color_model = 0
        self.normalization = 0
        self.computed = False

        self.result_floats_image = []
        self.result_rgba = []

        self.shader_program = None


    def load_shaders(self):
        if self.shader_program == None:
            with open('shaders/distance.vert', 'r') as file:
                VERTEX_SHADER = file.read()

            with open('shaders/distance.frag', 'r') as file:
                FRAGMENT_SHADER = file.read()

            self.shader_program = shaders.load_program(VERTEX_SHADER, FRAGMENT_SHADER)

            if self.shader_program == 0:
                print("Error with shaders distance")
                sys.exit(1)


    def create_buffers(self):
        # self.VAO = np.empty(1, dtype=np.uint32)
        glCreateVertexArrays(1,self.VAO)
        glBindVertexArray(self.VAO)

        # the buffer for the normalized image.It is used as a texture
        # if self.tex_input_normalized_image != 0:
        #     glDeleteTextures(1, self.tex_input_normalized_image)

        glCreateTextures(GL_TEXTURE_2D, 1, self.tex_input_normalized_image)
        glTextureStorage2D(self.tex_input_normalized_image, 1, GL_RGBA32F, self.width, self.height); #RGBA
        glTextureSubImage2D(self.tex_input_normalized_image, 0, 0, 0, self.width, self.height, GL_RGBA, GL_FLOAT, self.normalized_image)

        # for the result image
        # if self.tex_output_image != 0:
        #     glDeleteTextures(1, self.tex_output_image)

        glCreateTextures(GL_TEXTURE_2D, 1, self.tex_output_image)
        glTextureStorage2D(self.tex_output_image, 1, GL_R32F, self.normalized_image.shape[1],
                           self.normalized_image.shape[0]);  # R

        # The buffer for the positions data (x, y, value).It will be a SSBO
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

    def set_data(self, normalized_image, positions_data, valid_positions, lut, mhd_parameters,
                 position_normalization, value_normalization, probe_size):
        self.computed = False
        self.normalized_image = normalized_image
        self.positions_data = positions_data
        self.valid_positions = valid_positions
        self.width = self.normalized_image.shape[1]
        self.height = self.normalized_image.shape[0]
        self.lut = lut
        self.use_colors[0] = mhd_parameters[0]
        self.use_colors[1] = mhd_parameters[1]
        self.use_colors[2] = mhd_parameters[2]
        self.use_positions[0] = mhd_parameters[3]
        self.use_positions[1] = mhd_parameters[4]
        self.position_normalization = position_normalization
        self.value_normalization = value_normalization
        self.probe_size = probe_size


    def get_result_float_image(self):
        return self.result_floats_image

    def get_result_rgba_image(self):
        return self.result_rgba

    def update_layer(self):
        if self.computed == False:
            self.computed = True

            self.gl.makeCurrent()

            self.load_shaders()
            self.create_buffers()

            glUseProgram(self.shader_program)
            glBindVertexArray(self.VAO)
            glUseProgram(self.shader_program);
            glBindImageTexture(0, self.tex_input_normalized_image, 0, GL_FALSE, 0, GL_READ_WRITE, GL_RGBA32F)
            glBindImageTexture(1, self.tex_output_image, 0, GL_FALSE, 0, GL_READ_WRITE, GL_R32F)

            glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, self.buffer_positions_data)
            glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 1, self.buffer_valid_positions)
            # glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 2, self.buffer_colors)

            glUniform1i(0, int(self.width))
            glUniform1i(1, int(self.height))
            glUniform1i(2, int(len(self.positions_data)))

            # Probe
            # glUniform1i(3, int(self.probe))
            glUniform1i(3, int(self.probe_size))
            # Use colors
            glUniform1i(4, int(self.use_colors[0]))
            glUniform1i(5, int(self.use_colors[1]))
            glUniform1i(6, int(self.use_colors[2]))
            # Use positions
            glUniform1i(7, int(self.use_positions[0]))
            glUniform1i(8, int(self.use_positions[1]))

            # size of the Diagonal
            diagonal = 0;
            # RGB
            for i in range(len(self.use_colors)):
                if self.use_colors[i] == True:
                    diagonal = diagonal + 1.0

            # X
            if self.use_positions[0] == True:
                if self.position_normalization == True:
                    diagonal = diagonal + 1.0
                else:
                    if self.width >= self.height:
                        diagonal = diagonal + 1.0
                    else:
                        diagonal = diagonal + (float(self.width) / float(self.height))**2
                        # the shape is not squared so it is not a hypercube

            # Y
            if self.use_positions[1] == True:
                if self.position_normalization == True:
                    diagonal = diagonal + 1.0
                else:
                    if self.height > self.width:
                        diagonal = diagonal + 1.0
                    else:
                        diagonal = diagonal + (float(self.height) / float(self.width))**2
                        # the shape is not squared so it is not a hypercube

            # diagonal
            glUniform1f(9, math.sqrt(diagonal))

            # color model
            # glUniform1i(10, int(self.color_model))
            glUniform1i(10, int(0))

            # value normalization
            glUniform1i(11, int(self.value_normalization))

            # position normalization
            glUniform1i(12, int(self.position_normalization))

            #
            glViewport(0, 0, self.width, self.height)
            # draw a point for each pixel
            glDrawArrays(GL_POINTS, 0, self.width*self.height)

            # read the result
            if len(self.result_floats_image) == 0:
                self.result_floats_image = np.empty((self.height, self.width), dtype=np.float32)

            glBindTexture(GL_TEXTURE_2D, self.tex_output_image)
            glGetTexImage(GL_TEXTURE_2D, 0, GL_RED, GL_FLOAT, self.result_floats_image)

            # # Leer los píxeles de la ventana actual en OpenGL
            # glReadBuffer(GL_FRONT)
            # pixels = glReadPixels(0, 0, width, height, GL_RGB, GL_UNSIGNED_BYTE)
            #
            # # Convertir los datos a un array de NumPy
            # image = np.frombuffer(pixels, dtype=np.uint8).reshape(height, width, 3)
            #
            # # OpenGL lee de abajo hacia arriba, por lo que invertimos el array
            # image = np.flip(image, axis=0)

            glBindVertexArray(0)
            glUseProgram(0)

            glDeleteTextures(1, self.tex_input_normalized_image)
            glDeleteTextures(1, self.tex_output_image)
            glDeleteBuffers(1, self.buffer_positions_data)
            glDeleteBuffers(1, self.buffer_valid_positions)

            # glDeleteBuffers(1, self.buffer_colors)
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
