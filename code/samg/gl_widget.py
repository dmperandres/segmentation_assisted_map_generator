import sys
from PySide6.QtCore import Qt, Slot, QDir, QSize
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtGui import QMatrix4x4, QAction, QCursor
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


class gl_widget(QOpenGLWidget):
    def __init__(self, parent):
        super(gl_widget, self).__init__(parent)

        self.parent = parent
        self.shader_program = None

        self.vertices = []
        self.compute_vertices(100, 100)

        self.text_coord = np.array([[0.0, 0.0],
                                  [1.0, 0.0],
                                  [0.0, 1.0],
                                  [1.0, 1.0]],
                                 dtype=np.float32)
        self.text_coord_flat = np.ravel(self.text_coord)

        self.color = np.array([0, 0, 1], dtype=np.float32)

        self.VAO = GLuint(0)
        self.VBO_vertices = GLuint(0)
        self.VBO_text_coordinates = GLuint(0)
        self.texture =GLuint(0)

        self.scaling_factor = 1.0
        self.translation_x = 0.0
        self.translation_y = 0.0

        self.layers = []

        self.change_pos = False
        self.mode = globals.GL_WIDGET_MODE_POSITIONING
        self.copy_estate = -1
        self.point_found = False

        self.show_positions = False
        self.show_positions_number = False
        self.positions_texture = GLuint(0)

        self.image_width = None
        self.image_height = None

        self.setFocusPolicy(Qt.StrongFocus)


    def set_layers(self, layers):
        self.layers = layers

    def compute_vertices(self, width, height):
        self.half_width = width / 2
        self.half_height = height / 2

        del self.vertices
        self.vertices = np.array([[-self.half_width , -self.half_height, 0.0],
                                  [self.half_width, -self.half_height, 0.0],
                                  [-self.half_width, self.half_height, 0.0],
                                  [self.half_width, self.half_height, 0.0]],
                                 dtype=np.float32)
        self.vertices_flat = np.ravel(self.vertices)

    def initializeGL(self):
        # Configura el color de fondo
        glClearColor(0.8, 0.8, 0.8, 1.0)

        with open('shaders/basic_xmapslab.vert', 'r') as file:
            VERTEX_SHADER = file.read()

        with open('shaders/basic_xmapslab.frag', 'r') as file:
            FRAGMENT_SHADER = file.read()

        self.shader_program = shaders.load_program(VERTEX_SHADER, FRAGMENT_SHADER)

        if self.shader_program == 0:
            print("Error with shaders basic")
            sys.exit(1)

        # self.VAO = np.empty(1, dtype=np.uint32)
        glCreateVertexArrays(1,self.VAO)
        glBindVertexArray(self.VAO)

        # vertices
        glCreateBuffers(1, self.VBO_vertices);
        glNamedBufferStorage(self.VBO_vertices, self.vertices_flat.nbytes, None, GL_DYNAMIC_STORAGE_BIT | GL_MAP_WRITE_BIT )
        glVertexArrayVertexBuffer(self.VAO, 0, self.VBO_vertices, 0, 3*self.vertices_flat.strides[0])
        glVertexArrayAttribFormat(self.VAO, 0, 3, GL_FLOAT, GL_FALSE, 0);
        glEnableVertexArrayAttrib(self.VAO, 0);

        # texture coordinates
        glCreateBuffers(1, self.VBO_text_coordinates );
        glNamedBufferStorage(self.VBO_text_coordinates, self.text_coord_flat.nbytes, None, GL_DYNAMIC_STORAGE_BIT | GL_MAP_WRITE_BIT )
        glVertexArrayVertexBuffer(self.VAO, 1, self.VBO_text_coordinates, 0, 2*self.text_coord_flat.strides[0])
        glVertexArrayAttribFormat(self.VAO, 1, 2, GL_FLOAT, GL_FALSE, 0);
        glEnableVertexArrayAttrib(self.VAO, 1);

        # Put data
        # vertices
        glNamedBufferSubData(self.VBO_vertices, 0, self.vertices_flat.nbytes, self.vertices_flat);
        #texure coordinates
        glNamedBufferSubData(self.VBO_text_coordinates, 0, self.text_coord_flat.nbytes, self.text_coord_flat);

        glBindVertexArray(0)

        self.device_pixel_ratio = self.devicePixelRatio()


    def paintGL(self):
        self.makeCurrent()
        # get the maps that are visible
        visible_layers = []
        for pos in range(len(self.layers)):
            if self.layers[pos].visible == True:
                visible_layers.append(pos)

        num_visible_layers = len(visible_layers)

        if self.show_positions == True:
            num_visible_layers += 1

        parallel_projection = QMatrix4x4()
        window_width = self.width()
        window_height = self.height()

        parallel_projection.ortho(-int(window_width/2*self.scaling_factor), int(window_width/2*self.scaling_factor), -int(window_height/2*self.scaling_factor), int(window_height/2*self.scaling_factor), -1.0, 1.0)
        parallel_projection.translate(self.translation_x, self.translation_y, 0)

        glViewport(0, 0, int(round(window_width * self.device_pixel_ratio)), int(round(window_height * self.device_pixel_ratio)))

        # Limpia el buffer
        glClear(GL_COLOR_BUFFER_BIT)
        # Dibujar
        glUseProgram(self.shader_program)
        glBindVertexArray(self.VAO)

        # projection matrix
        glUniformMatrix4fv(10,1, False, parallel_projection.data())
        # num of textures to use
        glUniform1i(20, GLint(num_visible_layers))
        # background color
        white = (np.float32(1.0), np.float32(1.0), np.float32(1))
        glUniform3fv(21, 1, white)

        for pos in range(len(visible_layers)):
            # layer_type, layer_name, element_name, visible, transparency, inversion, texture
            glUniform1i(50 + pos, GLint(self.layers[visible_layers[pos]].layer_type))
            glUniform1f(60 + pos, GLfloat(self.layers[visible_layers[pos]].transparency))
            glUniform1i(70 + pos, GLint(self.layers[visible_layers[pos]].inversion))
            glUniform1i(80 + pos, GLint(0)) # color mixing
            glBindTextureUnit(pos, self.layers[visible_layers[pos]].texture)

        # for adding the positions
        if self.show_positions == True:
            pos = len(visible_layers)
            glUniform1i(50 + pos, GLint(0))
            glUniform1f(60 + pos, GLfloat(0))
            glUniform1i(70 + pos, GLint(0))
            glUniform1i(80 + pos, GLint(0))  # color mixing
            glBindTextureUnit(pos, self.positions_texture)

        # glPolygonMode(GL_FRONT, GL_FILL)
        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)

        glBindVertexArray(0)
        glUseProgram(0)

    def resizeGL(self, width, height):
        glViewport(0, 0, int(round(width * self.device_pixel_ratio)), int(round(height*self.device_pixel_ratio)))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Left:
            self.position[0] = self.position[0] - 0.1
        elif event.key() == Qt.Key_Right:
            self.position[0] = self.position[0] + 0.1
        elif event.key() == Qt.Key_Down:
            self.position[1] = self.position[1] - 0.1
        elif event.key() == Qt.Key_Up:
            self.position[1] = self.position[1] + 0.1
        elif event.key() == Qt.Key.Key_F1:
            self.mode = globals.GL_WIDGET_MODE_POSITIONING
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        elif event.key() == Qt.Key.Key_F2:
            self.mode = globals.GL_WIDGET_MODE_COPY_POSITION
            self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        elif event.key() == Qt.Key.Key_F3:
            self.mode = globals.GL_WIDGET_MODE_DELETE_POSITION
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.update()
        super().keyPressEvent(event)

    def mousePressEvent(self, event):
        self.initial_position_x = event.position().x()
        self.initial_position_y = event.position().y()

        if event.button() == Qt.MouseButton.LeftButton:
            if self.mode == globals.GL_WIDGET_MODE_POSITIONING:
                self.change_pos = True

        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.mode == globals.GL_WIDGET_MODE_POSITIONING:
                self.change_pos = False
        elif event.button() == Qt.MouseButton.RightButton:
            if self.mode == globals.GL_WIDGET_MODE_COPY_POSITION:
                if self.copy_estate == -1: # first point
                    self.end_position_x = event.position().x()
                    self.end_position_y = event.position().y()
                    self.copy_estate = 0
                    self.compute_position()
                    # check if a point was found in the last position
                    if self.point_found == True:
                        # go to next state
                        self.setCursor(QCursor(Qt.CursorShape.UpArrowCursor))
                    else: # back to initial state
                        self.copy_estate = -1
                elif self.copy_estate == 0: # second point
                    self.end_position_x = event.position().x()
                    self.end_position_y = event.position().y()
                    self.copy_estate = 1
                    self.compute_position()
                    # back to initial state
                    self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
                    self.copy_estate = -1
                    self.point_found = False
            elif self.mode == globals.GL_WIDGET_MODE_DELETE_POSITION:
                self.end_position_x = event.position().x()
                self.end_position_y = event.position().y()
                self.compute_position()

        self.update()

    def mouseMoveEvent(self, event):
        if self.mode == globals.GL_WIDGET_MODE_POSITIONING:
            if self.change_pos == True:
                self.translation_x += event.position().x()-self.initial_position_x
                self.translation_y += self.initial_position_y - event.position().y()
                self.initial_position_x = event.position().x()
                self.initial_position_y = event.position().y()
        self.update()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.mode == globals.GL_WIDGET_MODE_POSITIONING:
                self.translation_x = 0
                self.translation_y = 0
        elif event.button() == Qt.MouseButton.RightButton:
            if self.mode == globals.GL_WIDGET_MODE_POSITIONING:
                self.scaling_factor = 1.0

        self.update()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            self.scaling_factor *= 1.05
        elif delta < 0:
            self.scaling_factor /= 1.05

        self.update()

    def get_texture(self, image):
        # get the size to be used to compute the position
        self.image_width = image.shape[1]
        self.image_height = image.shape[0]

        texture = GLuint(0)
        glCreateTextures(GL_TEXTURE_2D, 1, texture)
        glTextureStorage2D(texture, 1, GL_RGBA8, image.shape[1], image.shape[0])
        glBindTexture(GL_TEXTURE_2D, texture)
        # glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        # glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTextureSubImage2D(texture, 0, 0, 0, image.shape[1], image.shape[0], GL_RGBA, GL_UNSIGNED_BYTE, image)

        self.compute_vertices(image.shape[1], image.shape[0])
        # vertices
        # glBindVertexArray(self.VAO)
        glNamedBufferSubData(self.VBO_vertices, 0, self.vertices_flat.nbytes, self.vertices_flat);
        # glBindVertexArray(0)
        self.update()
        return texture

    # def get_segments_texture(self, image):
    #     texture = GLuint(0)
    #     glCreateTextures(GL_TEXTURE_2D, 1, texture)
    #     glTextureStorage2D(texture, 1, GL_R8, image.shape[1], image.shape[0])
    #     glBindTexture(GL_TEXTURE_2D, texture)
    #     # glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
    #     # glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
    #     glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
    #     glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
    #     glTextureSubImage2D(texture, 0, 0, 0, image.shape[1], image.shape[0], GL_R8, GL_UNSIGNED_BYTE, image)
    #
    #     return texture

    def set_texture(self, texture):
        self.texture = texture
        self.update()

    def set_positions_texture(self, texture):
        self.positions_texture = texture

    def set_show_positions(self, value):
        self.show_positions = value
        self.update()

    def set_show_positions_number(self, value):
        self.show_positions_number = value
        self.update()

    def delete_texture(self, texture):
        if texture != 0:
            glDeleteTextures(1, texture)

    def update_texture(self, texture, image):
        glBindTexture(GL_TEXTURE_2D, texture)
        glTextureSubImage2D(texture, 0, 0, 0, image.shape[1], image.shape[0], GL_RGBA, GL_UNSIGNED_BYTE, image)
        self.update()

    def set_point_found(self, value):
        self.point_found = True


    def compute_position(self):
        if self.image_width == None:
            print("Error: not image_width")
            sys.exit(1)

        width = int(round(self.width() * self.scaling_factor))
        height = int(round(self.height() * self.scaling_factor))
        xmax = width//2
        xmin = -xmax
        ymax = height//2
        ymin = -ymax

        pos_x = 2*xmax * self.end_position_x / self.width() + xmin - self.translation_x
        pos_y = 2*ymax * self.end_position_y / self.height() + ymin + self.translation_y

        pos_x = int(round(pos_x + self.image_width / 2))
        pos_y = int(round(pos_y + self.image_height / 2))

        if pos_x >= 0 and pos_x < self.image_width and pos_y >=0 and pos_y < self.image_height:
            self.parent.update_positions(pos_x, self.image_height - pos_y, self.mode, self.copy_estate)