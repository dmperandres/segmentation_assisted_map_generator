import copy
import math
import sys
from PySide6.QtCore import Qt, Slot, QDir, QSize, Signal, QRect
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtGui import (QMatrix4x4, QAction, QPixmap, QIcon, QFontMetrics, QFont, QSurfaceFormat, QImage, QPainter,
                           QPen)
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
    QMenu,
    QLineEdit
)

import os
import numpy as np
import cv2
import glob
from OpenGL.GL import *
from scipy.interpolate import RBFInterpolator

import gl_widget
import layer_map_mhd
import project_data
import globals
import color_table
import palette_widget
import colorbar
import interpolation_parameters_widget
import fast_computation
import draw_positions
from options_widget import options_widget
import layer_map_mhd_segmentation
import layer_map_value_segmentation

from dataclasses import dataclass, field
from typing import List

auxiliary_folders = ['colormaps', 'icons', 'projects', 'shaders']

# layer_type, layer_name, element_name, visible, transparency, inversion, texture
@dataclass
class layer:
    layer_type : int
    layer_name: str
    element_name : str
    visible : bool
    transparency : float
    inversion : bool
    float_image : np.ndarray
    rgba_image : np.ndarray
    texture : GLuint
    # class palette in color_tables
    palette : color_table.palette

class button_icon(QPushButton):

    push_button = Signal(int, int)

    def __init__(self, row, col):
        super().__init__()
        self.row = row
        self.col = col

    def mousePressEvent(self, event):
        self.push_button.emit(self.row, self.col)


class main_window(QMainWindow):
    def __init__(self, parent = None):
        super().__init__()

        #check that the main auxiliary foders exist
        for folder in auxiliary_folders:
            # Comprobar si el directorio existe
            if not os.path.isdir(folder):
                QMessageBox.critical(self, 'Critical error', 'The folder '+ folder + ' does not exist. The program will be aborted')
                sys.exit(1)

        # load de colormaps
        self.color_table = color_table.color_table()

        self.layers = []
        self.count_layers = 1

        self.color_model = 'RGB'
        self.color_model_changed = False

        self.black_threshold = globals.BLACK_TRESHOLD
        self.white_threshold = globals.WHITE_TRESHOLD

        self.show_positions = False
        self.show_positions_number = False

        self.brush_out_circle = globals.BRUSH_OUT_CIRCLE
        self.brush_in_circle = globals.BRUSH_IN_CIRCLE

        self.label_text = globals.LABEL_TEXT_DEFAULT

        self.current_row = -1

        self.positions_texture = None

        self.position_font_size = globals.POSITION_FONT_SIZE
        self.position_out_circle_size = globals.POSITION_OUT_CIRCLE_SIZE
        self.position_font_color = globals.POSITION_FONT_COLOR
        self.position_out_circle_color = globals.POSITION_OUT_CIRCLE_COLOR
        self.position_in_circle_color = globals.POSITION_IN_CIRCLE_COLOR
        self.position_selection_out_circle_color = globals.POSITION_SELECTION_OUT_CIRCLE_COLOR
        self.position_font_scale = globals.POSITION_FONT_SCALE

        self.selected_point = -1
        self.selected_point_x = -1
        self.selected_point_y = -1

        self.null_value = 255

        self.show_connected_points = False
        self.connected_points = []

        self.valid_positions = []

        # self.kmeans_computed = True
        self.compute_kmeans_value = False
        self.kmeans_num_clusters_value = globals.KMEANS_NUM_CLUSTERS
        self.kmeans_num_iteractions_value = globals.KMEANS_NUM_ITERACTIONS

        # Configura la ventana
        main_widget = QWidget(self)
        layout_main = QHBoxLayout()

        # colorbar
        self.colorbar = colorbar.colorbar(globals.MAX_VALUE_COLORBAR_DEFAULT, self.height(), self.font(), scale = 1)

        # gl_widget
        self.gl_widget = gl_widget.gl_widget(self)
        format = QSurfaceFormat()
        format.setDepthBufferSize(24)
        # format.setStencilBufferSize(8)
        format.setVersion(4, 6)
        format.setProfile(QSurfaceFormat.CoreProfile)
        self.gl_widget.setFormat(format)
        self.gl_widget.set_layers(self.layers)

        # format = self.gl_widget.format()
        # version1 = format.version()
        # print(version1)

        self.tab_widget = QTabWidget()
        self.tab_widget.setMaximumWidth(globals.TAB_SIZE)
        self.tab_widget.setMinimumWidth(globals.TAB_SIZE)

        self.tab_layers = self.add_tab_layers()
        self.tab_widget.addTab (self.tab_layers, "Layers")

        self.tab_xrf = self.add_tab_xrf()
        self.tab_widget.addTab(self.tab_xrf, "XRF")

        self.tab_image = self.add_tab_image()
        self.tab_widget.addTab(self.tab_image, "Image")


        #
        layout_main.addWidget(self.colorbar)
        layout_main.addWidget(self.gl_widget)
        layout_main.addWidget(self.tab_widget)
        main_widget.setLayout(layout_main)

        # actions File
        action_load_project = QAction(QApplication.style().standardIcon(QStyle.SP_DialogOpenButton), 'Load project data', self)
        action_load_project.triggered.connect(self.load_project)

        action_save_single_layer  = QAction("Without colorbar", self)
        action_save_single_layer.triggered.connect(self.save_single_layer)

        action_save_single_layer_with_colorbar = QAction("With colorbar", self)
        action_save_single_layer_with_colorbar.triggered.connect(self.save_single_layer_with_colorbar)

        self.action_save_compose_image = QAction(QApplication.style().standardIcon(QStyle.SP_DialogSaveButton),"Save composed image", self)
        self.action_save_compose_image.setEnabled(False)
        self.action_save_compose_image.triggered.connect(self.save_compose_image)

        self.action_options = QAction('Options', self)
        self.action_options.setEnabled(False)
        self.action_options.triggered.connect(self.options_clicked)


        action_exit = QAction('Exit', self)
        action_exit.triggered.connect(QApplication.quit)

        # actions View
        self.action_view_positions = QAction('View positions', self)
        self.action_view_positions.setEnabled(False)
        self.action_view_positions.setCheckable(True)
        self.action_view_positions.triggered.connect(self.show_positions_changed)

        self.action_view_positions_number = QAction('View positions number', self)
        self.action_view_positions_number.setEnabled(False)
        self.action_view_positions_number.setCheckable(True)
        self.action_view_positions_number.triggered.connect(self.show_positions_number_changed)

        self.action_view_connected_points = QAction('View connected points', self)
        self.action_view_connected_points.setEnabled(False)
        self.action_view_connected_points.setCheckable(True)
        self.action_view_connected_points.triggered.connect(self.show_connected_points_changed)


        #
        self.menu_bar = self.menuBar()
        menu_file = self.menu_bar.addMenu('File')
        menu_file.addAction(action_load_project)
        menu_file.addSeparator()
        # submenu
        self.action_submenu_save_layer = QAction(QApplication.style().standardIcon(QStyle.SP_DialogSaveButton), "Save selected layer", self)
        submenu_save_selected_layer = QMenu(self)
        submenu_save_selected_layer.addAction(action_save_single_layer)
        submenu_save_selected_layer.addAction(action_save_single_layer_with_colorbar)
        self.action_submenu_save_layer.setMenu(submenu_save_selected_layer)
        self.action_submenu_save_layer.setEnabled(False)
        menu_file.addAction(self.action_submenu_save_layer)

        menu_file.addSeparator()
        menu_file.addAction(self.action_save_compose_image)
        menu_file.addSeparator()
        menu_file.addAction(self.action_options)
        menu_file.addSeparator()
        menu_file.addAction(action_exit)

        # menu View
        menu_view = self.menu_bar.addMenu('View')
        menu_view.addAction(self.action_view_positions)
        menu_view.addAction(self.action_view_positions_number)
        menu_view.addAction(self.action_view_connected_points)


        self.setCentralWidget(main_widget)

        self.setWindowTitle('Example')
        self.setGeometry(300, 300, 1000, 1000)

        # create the instance
        self.layer_mhd = layer_map_mhd.layer_map_mhd(self.gl_widget)
        # create the instance
        self.layer_mhd_segmentation = layer_map_mhd_segmentation.layer_map_mhd_segmentation(self.gl_widget)
        # create the instance
        self.layer_value_segmentation = layer_map_value_segmentation.layer_map_value_segmentation(self.gl_widget)

        self.icons = {}
        pixmap = QPixmap()
        pixmap.load('icons/button_visible.png')
        self.icons['visible'] = QIcon(pixmap)
        pixmap.load('icons/button_invisible.png')
        self.icons['invisible'] = QIcon(pixmap)

    def add_tab_layers(self):
        # Crea un widget
        tab_widget = QWidget()
        # Crea un layout y añade widgets al layout
        tab_vboxlayout = QVBoxLayout()

        # table layers
        size_policy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        size_policy.setVerticalStretch(1)
        self.table_layers = QTableWidget(self)
        self.table_layers.setSizePolicy(size_policy)

        # size_policy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        # self.table_layers = QTableWidget(self)
        # self.table_layers.setSizePolicy(size_policy)

        self.table_layers.setColumnCount(2)  # Dos columnas
        self.table_layers.setHorizontalHeaderLabels(['View', 'Name'])
        self.table_layers.horizontalHeader().setStretchLastSection(True)
        font = self.font()
        font_metric = QFontMetrics(font)
        width_char1 = font_metric.horizontalAdvance('_View_')
        self.table_layers.setColumnWidth(0, width_char1)

        self.table_layers.itemSelectionChanged.connect(self.on_selection_changed)

        # widget para cambiar los valores de transparencia
        self.frame_layer_parameters = QFrame()
        self.frame_layer_parameters.setFrameStyle(QFrame.Panel)

        gridlayout_layer_parameters = QGridLayout()

        label_transparency = QLabel('Transparency')
        self.slider_transparency = QSlider(Qt.Orientation.Horizontal)
        self.slider_transparency.setRange(0, 255)
        self.slider_transparency.setValue(0)
        self.slider_transparency.valueChanged.connect(self.transparency_changed)

        gridlayout_layer_parameters.addWidget(label_transparency, 0, 0)
        gridlayout_layer_parameters.addWidget(self.slider_transparency, 0, 1)

        self.frame_layer_parameters.setLayout(gridlayout_layer_parameters)
        self.frame_layer_parameters.hide()

        # Establece el layout en el widget
        separator = QFrame(self)
        separator.setFrameStyle(QFrame.HLine)

        button_remove_one = QPushButton('Remove selected map')
        button_remove_one.clicked.connect(self.remove_selected_map)

        button_remove_all = QPushButton('Remove all maps')
        button_remove_all.clicked.connect(self.remove_all_maps)

        # Establece el layout en el widget
        tab_vboxlayout.addWidget(self.table_layers)
        # parameters
        tab_vboxlayout.addWidget(self.frame_layer_parameters)
        tab_vboxlayout.addStretch()
        tab_vboxlayout.addWidget(separator)
        tab_vboxlayout.addWidget(button_remove_one)
        tab_vboxlayout.addWidget(button_remove_all)

        tab_widget.setLayout(tab_vboxlayout)

        tab_widget.setEnabled(False)

        return tab_widget

    def add_tab_xrf(self):
        # Crea un widget
        tab_widget = QWidget()
        # Crea un layout y añade widgets al layout
        tab_vboxlayout = QVBoxLayout()

        size_policy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        size_policy.setVerticalStretch(1)
        self.list_xrf = QListWidget(self)
        self.list_xrf.setSizePolicy(size_policy)
        self.list_xrf.setSelectionMode(QListWidget.MultiSelection)
        # Conectar la señal de cambio de selección a la función on_item_selected
        # self.list_xrf.itemSelectionChanged.connect(self.on_xrf_item_selected)

        widget_label = QFrame(self)
        widget_label.setFrameStyle(QFrame.Panel)
        gridlayout_label = QGridLayout()

        label_label = QLabel('Label')
        self.lineedit_label = QLineEdit(globals.LABEL_TEXT_DEFAULT)
        self.lineedit_label.textChanged.connect(self.label_changed)

        gridlayout_label.addWidget(label_label, 0, 0)
        gridlayout_label.addWidget(self.lineedit_label, 0, 1)

        widget_label.setLayout(gridlayout_label)

        #
        self.interpolation_parameters_widget = interpolation_parameters_widget.interpolation_parameters_widget()
        self.interpolation_parameters_widget.hide()

        self.button_show_interpolation_parameters = QPushButton('Show interpolation parameters')
        self.button_show_interpolation_parameters.clicked.connect(self.interpolation_parameters_changed)
        self.show_mhd_parameters = False

        self.palette_widget = palette_widget.palette_widget(self.color_table.colormap_names())
        self.palette_widget.hide()

        self.button_show_palette_parameters = QPushButton('Show palette parameters')
        self.button_show_palette_parameters.clicked.connect(self.palette_parameters_changed)
        self.show_palette_parameters = False

        # Establece el layout en el widget
        separator = QFrame(self)
        separator.setFrameStyle(QFrame.HLine)

        button_create_some = QPushButton('Create some maps')
        button_create_some.clicked.connect(self.create_some_maps)

        button_create_all = QPushButton('Create all maps')
        button_create_all.clicked.connect(self.create_all_maps)

        tab_vboxlayout.addWidget(self.list_xrf)
        tab_vboxlayout.addWidget(widget_label)
        tab_vboxlayout.addWidget(self.button_show_interpolation_parameters)
        tab_vboxlayout.addWidget(self.interpolation_parameters_widget)
        tab_vboxlayout.addWidget(self.button_show_palette_parameters)
        tab_vboxlayout.addWidget(self.palette_widget)
        tab_vboxlayout.addStretch()
        tab_vboxlayout.addWidget(separator)
        tab_vboxlayout.addWidget(button_create_some)
        tab_vboxlayout.addWidget(button_create_all)

        tab_widget.setLayout(tab_vboxlayout)

        tab_widget.setEnabled(False)

        return tab_widget

    def add_tab_image(self):
        # Crea un widget
        tab_widget = QWidget()
        # Crea un layout y añade widgets al layout
        tab_vboxlayout = QVBoxLayout()

        self.color_widget = QWidget()
        self.gridlayout_color = QGridLayout()

        label_color_model = QLabel('Model')
        combobox_color_model = QComboBox()
        combobox_color_model.addItems(globals.COLOR_MODELS)
        combobox_color_model.currentIndexChanged.connect(self.change_color_model)

        label_color_kmeans = QLabel('k-means')
        checkbox_color_kmeans = QCheckBox()
        checkbox_color_kmeans.stateChanged.connect(self.change_compute_kmeans)

        label_num_clusters = QLabel('Num clusters')
        spinBox_num_clusters = QSpinBox()
        spinBox_num_clusters.setMinimum(2)  # Valor mínimo
        spinBox_num_clusters.setMaximum(50)  # Valor máximo
        spinBox_num_clusters.setValue(globals.KMEANS_NUM_CLUSTERS)
        spinBox_num_clusters.valueChanged.connect(self.change_num_clusters)

        label_black_threshold = QLabel('Black threshold')
        slider_black_threshold = QSlider(Qt.Orientation.Horizontal)
        slider_black_threshold.setRange(0, 255)
        slider_black_threshold.setValue(globals.BLACK_TRESHOLD)
        slider_black_threshold.valueChanged.connect(self.change_black_threshold)

        label_white_threshold = QLabel('White threshold')
        slider_white_threshold = QSlider(Qt.Orientation.Horizontal)
        slider_white_threshold.setRange(0, 255)
        slider_white_threshold.setValue(globals.WHITE_TRESHOLD)
        slider_white_threshold.valueChanged.connect(self.change_white_threshold)

        self.gridlayout_color.addWidget(label_color_model, 0, 0)
        self.gridlayout_color.addWidget(combobox_color_model, 0, 1)
        self.gridlayout_color.addWidget(label_color_kmeans, 1, 0)
        self.gridlayout_color.addWidget(checkbox_color_kmeans, 1, 1)
        self.gridlayout_color.addWidget(label_num_clusters, 2, 0)
        self.gridlayout_color.addWidget(spinBox_num_clusters, 2, 1)
        self.gridlayout_color.addWidget(label_black_threshold, 3, 0)
        self.gridlayout_color.addWidget(slider_black_threshold, 3, 1)
        self.gridlayout_color.addWidget(label_white_threshold, 4, 0)
        self.gridlayout_color.addWidget(slider_white_threshold, 4, 1)

        self.color_widget.setLayout(self.gridlayout_color)

        #
        tab_vboxlayout.addWidget(self.color_widget)
        tab_vboxlayout.addStretch()

        tab_widget.setLayout(tab_vboxlayout)

        tab_widget.setEnabled(False)

        # hide
        if self.compute_kmeans_value == False:
            self.change_row_visibility(self.gridlayout_color, 2, False)

        if self.color_model == 'RGB':
            self.change_row_visibility(self.gridlayout_color, 3, False)
            self.change_row_visibility(self.gridlayout_color, 4, False)
        return tab_widget

    # def resizeEvent(self, event):
    #     # Obtener el nuevo tamaño de la ventana
    #     new_size = event.size()
    #     width = new_size.width()
    #     height = new_size.height()
    #
    #     self.colorbar.update_widget_size(height)
    #
    #     # Llamar al método de la superclase
    #     super().resizeEvent(event)


    def change_button(self,row):
        button = self.table_layers.cellWidget(row, 0)
        if self.layers[row].visible == True:
            button.setIcon(self.icons['visible'])
        else:
            button.setIcon(self.icons['invisible'])


    def add_layers_to_table(self):
        self.table_layers.blockSignals(True)
        for i in range(self.table_layers.rowCount()-1,-1,-1):
            self.table_layers.removeRow(i)

        for row in range(len(self.layers)):
            self.table_layers.insertRow(row)

            button = button_icon(row,0)
            if self.layers[row].visible == True:
                button.setIcon(self.icons['visible'])
            else:
                button.setIcon(self.icons['invisible'])
            button.push_button.connect(self.on_layer_push_button)
            self.table_layers.setCellWidget(row, 0, button)
            # layer_type, layer_name, element_name, visible, transparency, inversion, texture
            item = QTableWidgetItem(self.layers[row].layer_name)
            item.setToolTip(self.layers[row].layer_name)
            self.table_layers.setItem(row, 1, item)

        self.table_layers.blockSignals(False)


    def add_xrf_elements(self, xrf_elements):
        for element in xrf_elements.keys():
            item = QListWidgetItem(element)
            self.list_xrf.addItem(item)

        # Ajustar el tamaño del QListWidget para mostrar todos los elementos
        item_height = self.list_xrf.sizeHintForRow(0)
        items_count = self.list_xrf.count()
        margins = self.list_xrf.contentsMargins()

        # Calcular la altura necesaria: altura de todos los elementos + márgenes + un pequeño extra
        total_height = item_height * items_count + margins.top() + margins.bottom() + 2

        # Establecer la altura mínima del QListWidget
        self.list_xrf.setMinimumHeight(total_height)


    # def change_view(self, row):
    #     element_name = self.layers[row].element_name
    #     max_value = self.project.xrf_data[element_name].max_value
    #     self.colorbar.set_parameters(element_name, max_value, self.layers[row].palette)
    #
    #     self.table_layers.blockSignals(True)
    #     self.table_layers.selectRow(row)
    #     self.table_layers.blockSignals(False)

    def update_widgets_on_row_changed(self, row, button):
        # only change the widgets for mask and maps
        if self.layers[row].layer_type != globals.LAYER_TYPE_IMAGE:
            # show and update the frame with the transparency
            self.frame_layer_parameters.show()
            # put the current value
            self.slider_transparency.blockSignals(True)
            self.slider_transparency.setValue(self.layers[row].transparency * 255)
            self.slider_transparency.blockSignals(False)
            # change the state and the icon
            if button == True:
                # change the button
                self.layers[row].visible = not self.layers[row].visible
                self.change_button(row)
            # if the selected layer is a map, the colorbar must be show if the eye is open
            if self.layers[self.current_row].layer_type == globals.LAYER_TYPE_MAP:
                # update the colorbar with the data of the selected layer
                self.colorbar.set_visibility(self.layers[row].visible)
                element_name = self.layers[row].element_name
                max_value = self.project.xrf_data[element_name].max_value
                self.colorbar.set_parameters(element_name, max_value, self.layers[row].palette)

            # update the visibility of the selected row
            self.table_layers.blockSignals(True)
            self.table_layers.selectRow(row)
            self.table_layers.blockSignals(False)

            # update the visible texture
            self.gl_widget.set_texture(self.layers[self.current_row].texture)
            self.gl_widget.update()
        else:
            # hide the frame with transparency
            self.frame_layer_parameters.hide()

    @Slot()
    def on_layer_push_button(self, row, col):
        self.current_row = row
        self.update_widgets_on_row_changed(self.current_row, True)

    @Slot()
    def on_selection_changed(self):
        selected_items = self.table_layers.selectedItems()
        if selected_items:
            self.current_row = self.table_layers.currentRow()
            self.update_widgets_on_row_changed(self.current_row, False)

    @Slot()
    def label_changed(self, text):
        self.label_text = text

    @Slot()
    def interpolation_parameters_changed(self):
        self.show_mhd_parameters = not self.show_mhd_parameters
        if self.show_mhd_parameters == True:
            self.interpolation_parameters_widget.show()
            self.button_show_interpolation_parameters.setText('Hide interpolation parameters')
        else:
            self.interpolation_parameters_widget.hide()
            self.button_show_interpolation_parameters.setText('Show interpolation parameters')

    @Slot()
    def palette_parameters_changed(self):
        self.show_palette_parameters = not self.show_palette_parameters
        if self.show_palette_parameters == True:
            self.palette_widget.show()
            self.button_show_palette_parameters.setText('Hide palette parameters')
        else:
            self.palette_widget.hide()
            self.button_show_palette_parameters.setText('Show palette parameters')

    def get_layer_name(self, element, interpolation_method, position):
        # name = element+RGB+CCCPP+VN0+PN0+1
        layer_name = self.label_text +'_' + element + '_'

        # interpolation method
        layer_name = layer_name + globals.INTERPOLATION_METHODS_SHORT_TEXT[interpolation_method] + '_'

        if self.color_model == 'RGB':
            if self.mhd_parameters[0]:
                layer_name = layer_name + 'R'
            else:
                layer_name = layer_name + '_'
            if self.mhd_parameters[1]:
                layer_name = layer_name + 'G'
            else:
                layer_name = layer_name + '_'
            if self.mhd_parameters[2]:
                layer_name = layer_name + 'B'
            else:
                layer_name = layer_name + '_'
        elif self.color_model == 'HSV':
            if self.mhd_parameters[0]:
                layer_name = layer_name + 'H'
            else:
                layer_name = layer_name + '_'
            if self.mhd_parameters[1]:
                layer_name = layer_name + 'S'
            else:
                layer_name = layer_name + '_'
            if self.mhd_parameters[2]:
                layer_name = layer_name + 'V'
            else:
                layer_name = layer_name + '_'
        elif self.color_model == 'HLS':
            if self.mhd_parameters[0]:
                layer_name = layer_name + 'H'
            else:
                layer_name = layer_name + '_'
            if self.mhd_parameters[1]:
                layer_name = layer_name + 'L'
            else:
                layer_name = layer_name + '_'
            if self.mhd_parameters[2]:
                layer_name = layer_name + 'S'
            else:
                layer_name = layer_name + '_'

        if self.mhd_parameters[3]:
            layer_name = layer_name + 'X'
        else:
            layer_name = layer_name + '_'
        if self.mhd_parameters[4]:
            layer_name = layer_name + 'Y'
        else:
            layer_name = layer_name + '_'

        if self.value_normalization == True:
            layer_name = layer_name + '_VN1'
        else:
            layer_name = layer_name + '_VN0'

        if self.position_normalization == True:
            layer_name = layer_name + '_PN1'
        else:
            layer_name = layer_name + '_PN0'

        layer_name = layer_name + '_' + str(position)

        return layer_name


    @Slot()
    def create_some_maps(self):
        # get the selected elements
        selected_items = self.list_xrf.selectedItems()
        # Obtener el texto de los elementos seleccionados
        selected_elements = [item.text() for item in selected_items]

        progress = QProgressDialog("Working...", "Abort", 0, len(self.project.xrf_data), self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)

        # get the interpolation parameters
        (self.interpolation_method, self.mhd_parameters, self.position_normalization, self.value_normalization,
         self.probe_size) = self.interpolation_parameters_widget.get_parameters()
        # get the palette
        palette = self.palette_widget.get_palette_parameters()

        progress_value = 0
        for key in selected_elements:
            if self.interpolation_method == globals.INTERPOLATION_METHOD_MHD:
                float_image, rgba_image = self.compute_mhd(key, self.mhd_parameters, self.position_normalization,
                                                           self.value_normalization, self.probe_size, palette)
            elif self.interpolation_method == globals.INTERPOLATION_METHOD_SEGMENT_BASED_MHD:
                float_image, rgba_image = self.compute_mhd_segments(key, self.mhd_parameters, self.position_normalization,
                                                       self.value_normalization, self.probe_size, palette,
                                                       self.null_value)
            else:
                float_image, rgba_image = self.compute_value_segments(key, palette, self.interpolation_method,
                                                                      self.null_value)

            # layer_type, layer_name, element_name, visible, transparency, inversion, texture
            layer_name = self.get_layer_name(key, self.interpolation_method, self.count_layers)
            self.layers.append(layer(globals.LAYER_TYPE_MAP, layer_name, key, False, 0.0, False, float_image, rgba_image,
                                     self.gl_widget.get_texture(rgba_image), palette))
            self.count_layers += 1
            #
            progress_value += 1
            progress.setValue(progress_value)
            if (progress.wasCanceled()):
                break

        # if len(self.layers)==3:
        #     if self.layers[1].palette is self.layers[2].palette:
        #         print("iguales")

        progress.setValue(len(self.project.xrf_data))

        self.add_layers_to_table()

        self.tab_widget.setCurrentIndex(0)

    @Slot()
    def create_all_maps(self):
        progress = QProgressDialog("Working...", "Abort", 0, len(self.project.xrf_data), self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)

        progress_value = 0
        # get the interpolation parameters
        self.interpolation_method, self.mhd_parameters, self.position_normalization, self.value_normalization, self.probe_size = self.interpolation_parameters_widget.get_parameters()
        # get the palette
        palette = copy.deepcopy(self.palette_widget.get_palette_parameters())

        for key in self.project.xrf_data.keys():
            if self.interpolation_method == globals.INTERPOLATION_METHOD_MHD:
                float_image, rgba_image = self.compute_mhd(key, self.mhd_parameters, self.position_normalization,
                                                           self.value_normalization, self.probe_size, palette)
            elif self.interpolation_method == globals.INTERPOLATION_METHOD_SEGMENT_BASED_MHD:
                float_image, rgba_image = self.compute_mhd_segments(key, self.mhd_parameters, self.position_normalization,
                                                       self.value_normalization, self.probe_size, palette)

            # layer_type, layer_name, element_name, visible, transparency, inversion, texture
            layer_name = self.get_layer_name(key, self.interpolation_method, self.count_layers)
            self.layers.append(layer(globals.LAYER_TYPE_MAP, layer_name, key, False, 0.0, False, float_image, rgba_image,
                                     self.gl_widget.get_texture(rgba_image), palette))
            self.count_layers += 1
            progress_value += 1
            progress.setValue(progress_value)
            if (progress.wasCanceled()):
                break

        progress.setValue(len(self.project.xrf_data))

        self.add_layers_to_table()

        self.tab_widget.setCurrentIndex(0)

    @Slot()
    def remove_selected_map(self):
        row = self.table_layers.currentRow()
        if self.layers[row].layer_type == globals.LAYER_TYPE_MASK:
            self.gl_widget.delete_texture(self.layers[row].texture)
            del self.layers[row]

        self.add_layers_to_table()
        # search for the first visible map to select the row
        for pos in range(len(self.layers)-1, -1, -1):
            if self.layers[pos].visible == True:
                break

        if pos > 1:
            self.table_layers.selectRow(pos)
            self.gl_widget.set_texture(self.layers[pos].texture)
        else:
            self.gl_widget.set_texture(self.layers[0].texture)


    @Slot()
    def remove_all_maps(self):
        for pos in range(len(self.layers)-2, 0, -1):
            self.gl_widget.delete_texture(self.layers[pos].texture)
            del self.layers[pos]

        self.count_layers = 2
        self.add_layers_to_table()
        self.gl_widget.set_texture(self.layers[0].texture)

    @Slot()
    def transparency_changed(self, value):
        self.layers[self.current_row].transparency = value / 255.0
        self.gl_widget.update()


    @Slot()
    def change_color_model(self, index):
        if self.color_model != globals.COLOR_MODELS[index]:
            self.color_model = globals.COLOR_MODELS[index]
            if self.color_model == 'HLS':
                self.change_row_visibility(self.gridlayout_color, 3, True)
                self.change_row_visibility(self.gridlayout_color, 4, True)
            else:
                self.change_row_visibility(self.gridlayout_color, 3, False)
                self.change_row_visibility(self.gridlayout_color, 4, False)
            self.image_rgb_to_texture()

    @Slot()
    def change_compute_kmeans(self, state):
        if state == 2:
            self.compute_kmeans_value = True
            self.change_row_visibility(self.gridlayout_color, 2, True)
        elif state == 0:
            self.compute_kmeans_value = False
            self.change_row_visibility(self.gridlayout_color, 2, False)
        self.image_rgb_to_texture()


    @Slot()
    def change_num_clusters(self, value):
        self.kmeans_num_clusters_value = value
        self.image_rgb_to_texture()

    @Slot()
    def change_black_threshold(self, value):
        self.black_threshold = value
        self.image_rgb_to_texture()

    @Slot()
    def change_white_threshold(self, value):
        self.white_threshold = value
        self.image_rgb_to_texture()


    def compute_positions_image(self):
        # compute a size for the font and out circle
        if self.image_rgba.shape[0] < self.image_rgba.shape[1]:
            length = self.image_rgba.shape[0]
        else:
            length = self.image_rgba.shape[1]

        value = int(length / 100)
        self.position_font_size = value
        self.position_out_circle_size = value
        # add the positions image
        self.image_positions = np.zeros((self.image_rgba.shape), np.uint8)
        # image, coordinates_x, coordinates_y, in_color, out_color, out_radius, text_height, text_color
        draw_positions.draw_positions(self.image_positions, self.project.coordinates_x,
                                      self.project.coordinates_y, self.position_in_circle_color,
                                      self.position_out_circle_color, self.position_selection_out_circle_color,
                                      self.position_out_circle_size, self.position_font_size,
                                      self.position_font_color, self.show_positions_number, self.selected_point,
                                      self.show_connected_points, self.connected_points)

        if self.positions_texture == None:
            self.positions_texture = self.gl_widget.get_texture(self.image_positions)
            self.gl_widget.set_positions_texture(self.positions_texture)
        else:
            self.gl_widget.update_texture(self.positions_texture, self.image_positions)


    @Slot()
    def show_positions_changed(self):
        if self.action_view_positions.isChecked() == True:
            self.show_positions = True
            self.action_view_positions_number.setEnabled(True)
            self.action_view_connected_points.setEnabled(True)
        else:
            self.show_positions = False
            self.action_view_positions_number.setEnabled(False)
            self.action_view_connected_points.setEnabled(False)
        # compute the texture
        self.compute_positions_image()
        self.gl_widget.set_show_positions(self.show_positions)


    @Slot()
    def show_positions_number_changed(self):
        if self.action_view_positions_number.isChecked() == True:
            self.show_positions_number = True
        else:
            self.show_positions_number = False
        # compute the texture
        self.compute_positions_image()
        self.gl_widget.set_show_positions_number(self.show_positions_number)

    @Slot()
    def show_connected_points_changed(self):
        if self.action_view_connected_points.isChecked() == True:
            self.show_connected_points = True
        else:
            self.show_connected_points = False
        # compute the texture
        self.compute_positions_image()
        self.gl_widget.set_show_positions_number(self.show_positions)


    @Slot()
    def save_single_layer(self):
        if self.current_row >= 0:
            self.save_layer_image(self.layers[self.current_row])
            QMessageBox.information(self, "Information", "The file has been saved correctly.")
        else:
            QMessageBox.information(self, "Information", "Please, select a layer.")

    @Slot()
    def save_single_layer_with_colorbar(self):
        if self.current_row >= 0:
            self.save_layer_image_with_colorbar(self.layers[self.current_row])
            QMessageBox.information(self, "Information", "The file has been saved correctly.")
        else:
            QMessageBox.information(self, "Information", "Please, select a layer.")


    @Slot()
    def save_compose_image(self):
        pass

    @Slot()
    def options_clicked(self):
        options =  options_widget(self)
        options.show()

    def set_options_values(self, values):
        # font_size, out_circle_size, font_color, out_circle_color, in_color_size, font_scale
        self.position_font_size = values[0]
        self.position_out_circle_size = values[1]
        self.position_font_color = values[2]
        self.position_out_circle_color = values[3]
        self.position_in_circle_color = values[4]
        self.position_selection_out_circle_color = values[5]
        self.position_font_scale = values[6]
        # recreate the positions image
        self.image_positions = np.zeros((self.image_rgba.shape), np.uint8)
        # image, coordinates_x, coordinates_y, in_color, out_color, out_radius, text_height, text_color
        draw_positions.draw_positions(self.image_positions, self.project.coordinates_x,
                                      self.project.coordinates_y, self.position_in_circle_color,
                                      self.position_out_circle_color, self.position_selection_out_circle_color,
                                      self.position_out_circle_size,
                                      self.position_font_size, self.position_font_color, self.show_positions_number,
                                      self.selected_point, self.show_connected_points, self.connected_points)
        self.gl_widget.update_texture(self.positions_texture, self.image_positions)


    def get_options_values(self):
        return (self.position_font_size, self.position_out_circle_size, self.position_font_color,
                self.position_out_circle_color,  self.position_in_circle_color,
                self.position_selection_out_circle_color, self.position_font_scale)


    def save_layer_image(self, layer):
        # get the image
        if layer.layer_type == globals.LAYER_TYPE_IMAGE:
            image = cv2.cvtColor(self.image_processed, cv2.COLOR_RGB2RGBA).copy()
            file_name = self.project_dir + '/xrf/maps/' + layer.layer_name +'_' + self.color_model + '.png'
        else:
            image = layer.rgba_image.copy()
            file_name = self.project_dir + '/xrf/maps/' + layer.layer_name + '.png'

        # image, coordinates_x, coordinates_y, in_color, out_color, selection_out_color, out_radius,
        # text_height, text_color, draw_positions_number, selected_point, draw_connected_points, connected_points
        if self.show_positions == True:
            draw_positions.draw_positions(image, self.project.coordinates_x,
                                          self.project.coordinates_y, self.position_in_circle_color,
                                          self.position_out_circle_color, self.position_selection_out_circle_color,
                                          self.position_out_circle_size,
                                          self.position_font_size, self.position_font_color, self.show_positions_number,
                                          self.selected_point, self.show_connected_points, self.connected_points)
            # draw_positions.draw_positions(image, self.project.coordinates_x,
            #                           self.project.coordinates_y, [255, 255, 0, 255], [0, 0, 255, 255], 40, 40,
            #                           [0, 255, 0, 255])
        qimage = QImage(image, image.shape[1], image.shape[0], image.strides[0], QImage.Format_RGBA8888)
        qimage.mirror()
        qimage.save(file_name,'PNG')


    def save_layer_image_with_colorbar(self, layer):
        # get the image
        if layer.layer_type == globals.LAYER_TYPE_IMAGE:
            image = cv2.cvtColor(self.image_processed, cv2.COLOR_RGB2RGBA).copy()
            file_name = self.project_dir + '/xrf/maps/' + layer.layer_name +'_' + self.color_model + '.png'
        else:
            image = layer.rgba_image.copy()
            file_name = self.project_dir + '/xrf/maps/' + layer.layer_name + '.png'

        # image, coordinates_x, coordinates_y, in_color, out_color, out_radius, text_height, text_color
        if self.show_positions == True:
            # draw_positions.draw_positions(image, self.project.coordinates_x,
            #                           self.project.coordinates_y, [255, 255, 0, 255], [0, 0, 255, 255], 40, 40,
            #                           [0, 255, 0, 255])
            draw_positions.draw_positions(image, self.project.coordinates_x,
                                          self.project.coordinates_y, self.position_in_circle_color,
                                          self.position_out_circle_color, self.position_selection_out_circle_color,
                                          self.position_out_circle_size,
                                          self.position_font_size, self.position_font_color, self.show_positions_number,
                                          self.selected_point, self.show_connected_points, self.connected_points)

        map_image = QImage(image, image.shape[1], image.shape[0], image.strides[0], QImage.Format_RGBA8888)
        map_image.mirror()

        # create an image that includes the map and the colorbar
        colorbar_size = colorbar.colorbar(self.maximum_value, self.height(), self.font(), scale = self.position_font_scale)
        colorbar_width = colorbar_size.get_width()

        image_width = image.shape[1]
        image_height = image.shape[0]

        white_space = 5
        line_width = 3

        image_total_width = image_width + colorbar_width + 4 * white_space + 2 * line_width + globals.COLORBAR_SQUARE_SIZE
        image_total_height = image_height + 4 * white_space + 2 * line_width

        # final_image = np.full((image_total_height, image_total_with, 4), 255, np.uint8)

        result_image = QImage(image_total_width, image_total_height, QImage.Format_RGBA8888)
        result_image.fill(Qt.white)

        painter  = QPainter(result_image)
        painter.drawImage(2 * white_space + line_width, 2 * white_space + line_width, map_image)

        pen = QPen()
        pen.setWidth(line_width)
        painter.setPen(pen)

        # draw the black border
        rect = QRect(white_space,white_space, image_width + 2 * white_space + 2 * line_width,
                     image_height + 2 * white_space + 2 * line_width)
        painter.drawRect(rect)

        # draw the colorbar
        # update the colorbar widget size
        # max_value, height, font, painter
        colorbar1 = colorbar.colorbar(self.maximum_value, image_total_height - 2 * globals.COLORBAR_SQUARE_SIZE,
                                      self.font(), painter, scale = self.position_font_scale)
        element_name = layer.element_name
        max_value = self.project.xrf_data[element_name].max_value
        colorbar1.set_visibility(True)

        painter.translate(image_width + 4 * white_space + 2 * line_width + 2 *white_space + globals.COLORBAR_SQUARE_SIZE,
                          globals.COLORBAR_SQUARE_SIZE)
        colorbar1.set_parameters(element_name, max_value, layer.palette)

        painter.end()

        # result_image.mirror()
        result_image.save(file_name,'PNG')


    def process_image(self):
        if self.color_model == 'HSV':
            self.image_processed = cv2.cvtColor(self.image_processed, cv2.COLOR_RGB2HSV)
        elif self.color_model == 'HLS':
            self.image_processed = cv2.cvtColor(self.image_processed, cv2.COLOR_RGB2HLS)
            self.image_processed[:, :, 2] = 255
            fast_computation.process_hsl(self.image_processed, self.black_threshold, self.white_threshold)
            self.image_processed = cv2.cvtColor(self.image_processed, cv2.COLOR_HLS2RGB)
        # k-means
        if self.compute_kmeans_value == True:
            self.image_processed = self.k_means(self.image_processed, self.kmeans_num_clusters_value,
                                                self.kmeans_num_iteractions_value)


    def image_rgb_to_texture(self):
        # update the image
        self.image_processed = self.image_rgb.copy()
        # and process it
        self.process_image()
        # convert  back to RGBA
        self.image_rgba = cv2.cvtColor(self.image_processed, cv2.COLOR_RGB2RGBA)
        # convert to float32
        image_fp32 = self.image_rgba.astype(np.float32)
        # normalize
        self.normalized_image = image_fp32 / 255.0
        self.gl_widget.update_texture(self.layers[0].texture, self.image_rgba)


    def load_image(self, file_name):
        """ load pixmap from filename """
        image_bgr = cv2.imread(file_name)
        # self.image_width = self.painting_widget.width()
        # self.image_height = int(self.image_width * image_bgr.shape[0] / image_bgr.shape[1])
        nw = int(round(image_bgr.shape[1]/4.0))*4
        nh = int(round(image_bgr.shape[0]/4.0))*4
        image_bgr = cv2.resize(image_bgr, (nw, nh))
        self.image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        self.image_rgb = cv2.flip(self.image_rgb, 0)
        self.image_loaded = True
        # create the copy
        self.image_processed = self.image_rgb.copy()
        # and process it
        self.process_image()
        # convert  back to RGBA
        self.image_rgba = cv2.cvtColor(self.image_processed, cv2.COLOR_RGB2RGBA)
        # convert to float32
        image_fp32 = self.image_rgba.astype(np.float32)
        # normalize
        self.normalized_image = image_fp32 / 255.0
        # put the image as a texture
        texture = self.gl_widget.get_texture(self.image_rgba)
        if texture == 0:
            sys.exit(1)
        # layer_type, layer_name, element_name, visible, transparency, inversion, texture, palette
        palette = color_table.palette()
        image1 = np.empty((500, 600), dtype=np.float32)
        self.layers.append(layer(globals.LAYER_TYPE_IMAGE, 'color_image', 'none', True, 0.0, False, image1, self.image_rgba, texture, palette))
        # set the visible texture
        self.gl_widget.set_texture(texture)
        self. add_layers_to_table()

        self.update()


    def load_color_mask_image(self, file_name):
        """ load pixmap from filename """
        color_mask_image = cv2.imread(file_name, cv2.IMREAD_UNCHANGED)
        # self.image_width = self.painting_widget.width()
        # self.image_height = int(self.image_width * color_mask.shape[0] / color_mask.shape[1])
        nw = int(round(color_mask_image.shape[1]/4.0))*4
        nh = int(round(color_mask_image.shape[0]/4.0))*4
        color_mask_image = cv2.resize(color_mask_image, (nw, nh))
        self.color_mask_image = cv2.flip(color_mask_image, 0)
        #
        texture = self.gl_widget.get_texture(self.color_mask_image)
        if texture == 0:
            sys.exit(1)
        # layer_type, layer_name, element_name, visible, transparency, inversion, texture, palette
        palette = color_table.palette()
        image1 = np.empty((500, 600), dtype=np.float32)
        self.layers.append(layer(globals.LAYER_TYPE_MASK, 'color_mask', 'none', False, 0.0, False, image1,
                                 self.color_mask_image, texture, palette))
        # set the visible texture
        # self.gl_widget.set_texture(texture)
        self. add_layers_to_table()
        self.update()

    def load_segments_mask_image(self, file_name):
        """ load pixmap from filename """
        segments_mask_image = cv2.imread(file_name, cv2.IMREAD_UNCHANGED)
        # self.image_width = self.painting_widget.width()
        # self.image_height = int(self.image_width * color_mask.shape[0] / color_mask.shape[1])
        nw = int(round(segments_mask_image.shape[1]/4.0))*4
        nh = int(round(segments_mask_image.shape[0]/4.0))*4
        segments_mask_image = cv2.resize(segments_mask_image, (nw, nh))
        self.segments_mask_image = cv2.flip(segments_mask_image, 0)
        #
        # self.segments_texture = self.gl_widget.get_segments_texture(self.segments_mask)
        # if texture == 0:
        #     sys.exit(1)

    def get_image_file_name(self, path, filter):
        dialog = QFileDialog(self, "Load image")
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setAcceptMode(QFileDialog.AcceptOpen)
        dialog.setNameFilter(filter)
        dialog.setDirectory(QDir(path + '/data'))
        if dialog.exec() == QFileDialog.Accepted:
            if dialog.selectedFiles():
                return dialog.selectedFiles()[0]


    @Slot()
    def load_project(self):
        dialog = QFileDialog(self, "Load project")
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOptions(QFileDialog.DontUseNativeDialog)
        # dialog.setAcceptMode(QFileDialog.AcceptOpen)
        # dialog.setNameFilter("Project files (*.csv)")
        dialog.setDirectory(QDir(os.getcwd() + '/projects'))
        # dialog.setDirectory(QDir('./projects'))

        if dialog.exec() == QFileDialog.Accepted:
            if dialog.selectedFiles():
                # check the set of images in the project
                self.project_dir = dialog.selectedFiles()[0]
                pattern = self.project_dir + '/images/*.png'
                # Usar glob para encontrar archivos que coincidan con el patrón
                list_images = glob.glob(pattern)
                if len(list_images)==0:
                    QMessageBox.critical(self, "Critical error", "There is not image and the applications is aborted")
                    sys.exit(1)
                elif len(list_images)>1:
                    file_name = self.get_image_file_name(self.project_dir + '/images', 'Image files (*.png *.jpg)')
                else:
                    file_name = list_images[0]

                self.load_image(file_name)

                # load the color mask
                pattern = self.project_dir + '/masks/color_mask*.png'
                # Usar glob para encontrar archivos que coincidan con el patrón
                list_images = glob.glob(pattern)
                if len(list_images)==0:
                    QMessageBox.critical(self, "Critical error", "There is not color mask image and the applications is aborted")
                    sys.exit(1)
                elif len(list_images)>1:
                    file_name = self.get_image_file_name(self.project_dir + '/masks', 'Color masks (color_mask*.png)')
                else:
                    file_name = list_images[0]

                self.load_color_mask_image(file_name)

                # load the segments' IDs image
                pattern = self.project_dir + '/masks/segments_mask*.png'
                # Usar glob para encontrar archivos que coincidan con el patrón
                list_images = glob.glob(pattern)
                if len(list_images) == 0:
                    QMessageBox.critical(self, "Critical error",
                                         "There is not segments mask image and the applications is aborted")
                    sys.exit(1)
                elif len(list_images) > 1:
                    file_name = self.get_image_file_name(self.project_dir + '/masks', 'Segments masks (segments_mask*.png)')
                else:
                    file_name = list_images[0]

                self.load_segments_mask_image(file_name)


                # load de data
                self.project = project_data.project_data()
                self.project.load(self.project_dir + '/project_data.csv', self.image_rgb.shape[1],
                                  self.image_rgb.shape[0])
                # get the maximum of the maximums
                self.maximum_value = max([value.max_value for value in self.project.xrf_data.values()])
                # create the list with the information of the positions
                self.valid_positions = np.full((len(self.project.coordinates_x),), 1, np.uint32)

                # update the colorbar widget size
                self.colorbar.set_max_value(self.maximum_value)
                self.colorbar.update_widget_size(self.height())
                # add the elements
                self.add_xrf_elements(self.project.xrf_data)

                # print(self.image_positions[0,0])
                # self.gl_widget.update_texture(self.positions_texture, self.image_positions)

                # do the RBF
                # print("Por aqui")
                # xobs = np.column_stack((self.project.coordinates_y, self.project.coordinates_x))
                # yobs = self.project.xrf_data['As']
                # xgrid = np.mgrid[0:self.image_rgba.shape[0], 0:self.image_rgba.shape[1]]
                # xflat = xgrid.reshape(2, -1).T
                # yflat = RBFInterpolator(xobs, yobs)(xflat)
                # ygrid = yflat.reshape(len(self.project.coordinates_y), len(self.project.coordinates_x))
                #
                # print("ygrid ", ygrid[0, 0])

                # enable
                self.tab_layers.setEnabled(True)
                self.tab_xrf.setEnabled(True)
                self.tab_image.setEnabled(True)

                self.action_submenu_save_layer.setEnabled(True)
                self.action_save_compose_image.setEnabled(True)
                self.action_view_positions.setEnabled(True)
                self.action_options.setEnabled(True)

    # def compute_mhd(self):
    #     # x, y, value : int, int, float
    #     data_type = np.dtype([('x', np.float32), ('y', np.float32), ('value', np.float32)])
    #
    #     self.positions_data = np.array([(100, 100, 0.15), (300, 200, 0.75)], dtype=data_type)
    #
    #     #compute the colors
    #     self.colors = np.zeros((len(self.positions_data),4),np.float32)
    #     for pos in range(len(self.positions_data)):
    #         self.colors[pos] = self.normalized_image[int(self.positions_data[pos]['x']),int(self.positions_data[pos]['y'])]
    #
    #     self.valid_positions = np.full((len(self.positions_data),), True, dtype=bool)
    #
    #     self.layer_mhd.set_data(self.normalized_image, self.positions_data, self.colors, self.valid_positions)
    #     self.layer_mhd.update()

    def compute_mhd(self, element, mhd_parameters, position_normalization, value_normalization, probe_size, palette):
        # compute the colors
        colors = np.zeros((len(self.project.coordinates_x), 4), np.float32)
        for pos in range(len(self.project.coordinates_x)):
            # the image is OpenCV numpy, (y,x) instead of (x,y)
            colors[pos] = self.normalized_image[int(self.project.coordinates_y[pos]), int(self.project.coordinates_x[pos])]

        # x, y, value, Color
        # Definir un tipo de datos compuesto
        # dt = np.dtype([('x', np.float32), ('y', np.float32), ('color', np.float32, (3,)), ('segment_id', np.uint8)])
        # data_type = np.dtype([('x', np.float32), ('y', np.float32), ('value', np.float32), ('color', np.float32, (4,))])

        # ¡¡ importante¡¡ Dado que el color son 4 flotantes, segun las reglas std430 de GLSL, vec4 necesita alinearse a
        # 16 bytes. Si solo pongo x,y, y value, no se produce el alieneamiento a 16 bytes y se producen errores en la lectura
        # por eso se añade una variable más para que se produzca el ajuste
        data_type = np.dtype([('x', np.float32), ('y', np.float32), ('value', np.float32), ('segment_id', np.int32), ('color', np.float32, (4,))])

        # positions_data = np.stack((self.project.coordinates_x, self.project.coordinates_y, self.project.xrf_data[element].values), axis=1).astype(np.float32)
        # positions_data = np.stack(
        #     (self.project.coordinates_x, self.project.coordinates_y, self.project.xrf_data[element].values, colors),
        #     axis=1, dtype=dt)

        # Crear un array vacío con el tipo de datos compuesto
        positions_data = np.empty([len(self.project.coordinates_x)], dtype=data_type)

        # Asignar los valores a las respectivas columnas
        positions_data['x'] = self.project.coordinates_x
        positions_data['y'] = self.project.coordinates_y
        positions_data['value'] = self.project.xrf_data[element].values
        positions_data['color'] = colors

        # print(positions_data.tobytes())
        # print(positions_data.dtype.fields)

        # for pos in range(len(project_data.coordinates_x)):
        #     positions_data.append((self.project.coordinate_x))
        # in BOTTOM_LEFT CS
        # positions_data = np.array([(250, 250, 0.0), (750, 250, 0.5), (250, 750, 1), (750, 750, 0) ], np.float32)
        # positions_data = np.array([(250, 750, 1), (750, 750, 0), (250, 250, 0.0), (750, 250, 0.2)], np.float32)

        # valid_positions = np.full((len(positions_data),), True, dtype=bool)
        # valid_positions = valid_positions.astype(np.int32)

        # lut = np.zeros((256, 1, 3), dtype=np.uint8)
        # # lut[:, 0, 0] = np.arange(256) # canal rojo 0
        # color1 = np.array([1, 1, 1])
        # color2 = np.array([1, 0, 0])
        # for i in range(256):
        #     t = float(i) / float(255)
        #     lut[i] = ((1 - t) * color1 + t * color2) * 255.0
        #     lut[i] = np.round(lut[i]).astype(int)

        lut = self.color_table.create(palette)

        self.layer_mhd.set_data(self.normalized_image, positions_data, self.valid_positions, lut, mhd_parameters,
                                position_normalization, value_normalization, probe_size)
        self.layer_mhd.update_layer()

        return self.layer_mhd.get_result_float_image(), self.layer_mhd.get_result_rgba_image()


    def compute_mhd_segments(self, element, mhd_parameters, position_normalization, value_normalization, probe_size,
                             palette, null_value):
        # compute the colors
        colors = np.zeros((len(self.project.coordinates_x), 4), np.float32)
        for pos in range(len(self.project.coordinates_x)):
            # the image is OpenCV numpy, (y,x) instead of (x,y)
            colors[pos] = self.normalized_image[int(self.project.coordinates_y[pos]), int(self.project.coordinates_x[pos])]

        # compute the segments ids
        segments_ids = np.zeros((len(self.project.coordinates_x)), np.uint32)
        for pos in range(len(self.project.coordinates_x)):
            # the image is OpenCV numpy, (y,x) instead of (x,y)
            segments_ids[pos] = self.segments_mask_image[
                int(self.project.coordinates_y[pos]), int(self.project.coordinates_x[pos])]


        # print("segments ", segments_ids)
        # x, y, value, Color
        # Definir un tipo de datos compuesto
        # dt = np.dtype([('x', np.float32), ('y', np.float32), ('color', np.float32, (3,)), ('segment_id', np.uint8)])
        # data_type = np.dtype([('x', np.float32), ('y', np.float32), ('value', np.float32), ('color', np.float32, (4,))])

        # ¡¡ importante¡¡ Dado que el color son 4 flotantes, segun las reglas std430 de GLSL, vec4 necesita alinearse a
        # 16 bytes. Si solo pongo x,y, y value, no se produce el alieneamiento a 16 bytes y se producen errores en la lectura
        # por eso se añade una variable más para que se produzca el ajuste
        data_type = np.dtype([('x', np.float32), ('y', np.float32), ('value', np.float32), ('segment_id', np.int32),
                              ('color', np.float32, (4,))])

        # positions_data = np.stack((self.project.coordinates_x, self.project.coordinates_y, self.project.xrf_data[element].values), axis=1).astype(np.float32)
        # positions_data = np.stack(
        #     (self.project.coordinates_x, self.project.coordinates_y, self.project.xrf_data[element].values, colors),
        #     axis=1, dtype=dt)

        # Crear un array vacío con el tipo de datos compuesto
        positions_data = np.empty([len(self.project.coordinates_x)], dtype=data_type)

        # Asignar los valores a las respectivas columnas
        positions_data['x'] = self.project.coordinates_x
        positions_data['y'] = self.project.coordinates_y
        positions_data['value'] = self.project.xrf_data[element].values
        positions_data['segment_id'] = segments_ids
        positions_data['color'] = colors

        # print(positions_data.tobytes())
        # print(positions_data.dtype.fields)

        # for pos in range(len(project_data.coordinates_x)):
        #     positions_data.append((self.project.coordinate_x))
        # in BOTTOM_LEFT CS
        # positions_data = np.array([(250, 250, 0.0), (750, 250, 0.5), (250, 750, 1), (750, 750, 0) ], np.float32)
        # positions_data = np.array([(250, 750, 1), (750, 750, 0), (250, 250, 0.0), (750, 250, 0.2)], np.float32)

        # valid_positions = np.full((len(positions_data),), True, dtype=bool)
        # valid_positions = valid_positions.astype(np.int32)

        # lut = np.zeros((256, 1, 3), dtype=np.uint8)
        # # lut[:, 0, 0] = np.arange(256) # canal rojo 0
        # color1 = np.array([1, 1, 1])
        # color2 = np.array([1, 0, 0])
        # for i in range(256):
        #     t = float(i) / float(255)
        #     lut[i] = ((1 - t) * color1 + t * color2) * 255.0
        #     lut[i] = np.round(lut[i]).astype(int)

        lut = self.color_table.create(palette)

        self.layer_mhd_segmentation.set_data(self.normalized_image, self.segments_mask_image,  positions_data,
                                             self.valid_positions, lut, mhd_parameters,
                                             position_normalization, value_normalization, probe_size, null_value)
        self.layer_mhd_segmentation.update_layer()

        return self.layer_mhd_segmentation.get_result_float_image(), self.layer_mhd_segmentation.get_result_rgba_image()

    def compute_value_segments(self, element, palette, mode, null_value):
        # compute the colors
        # colors = np.zeros((len(self.project.coordinates_x), 4), np.float32)
        # for pos in range(len(self.project.coordinates_x)):
        #     # the image is OpenCV numpy, (y,x) instead of (x,y)
        #     colors[pos] = self.normalized_image[int(self.project.coordinates_y[pos]), int(self.project.coordinates_x[pos])]

        # compute the segments ids
        segments_ids = np.zeros((len(self.project.coordinates_x)), np.uint32)
        for pos in range(len(self.project.coordinates_x)):
            # the image is OpenCV numpy, (y,x) instead of (x,y)
            segments_ids[pos] = self.segments_mask_image[
                int(self.project.coordinates_y[pos]), int(self.project.coordinates_x[pos])]

        # ¡¡ importante¡¡ Dado que el color son 4 flotantes, segun las reglas std430 de GLSL, vec4 necesita alinearse a
        # 16 bytes. Si solo pongo x,y, y value, no se produce el alieneamiento a 16 bytes y se producen errores en la lectura
        # por eso se añade una variable más para que se produzca el ajuste
        data_type = np.dtype([('x', np.float32), ('y', np.float32), ('value', np.float32), ('segment_id', np.int32)])

        # Crear un array vacío con el tipo de datos compuesto
        positions_data = np.empty([len(self.project.coordinates_x)], dtype=data_type)

        # Asignar los valores a las respectivas columnas
        positions_data['x'] = self.project.coordinates_x
        positions_data['y'] = self.project.coordinates_y
        positions_data['value'] = self.project.xrf_data[element].values
        positions_data['segment_id'] = segments_ids
        # positions_data['color'] = colors

        # valid_positions = np.full((len(positions_data),), True, dtype=bool)
        # valid_positions = valid_positions.astype(np.int32)

        lut = self.color_table.create(palette)

        self.layer_value_segmentation.set_data(self.segments_mask_image,  positions_data, self.valid_positions, lut,
                                             mode, null_value)
        self.layer_value_segmentation.update_layer()

        return self.layer_value_segmentation.get_result_float_image(), self.layer_value_segmentation.get_result_rgba_image()


    def k_means(self, image, num_clusters, num_iteractions):
        Z = image.reshape((-1, 3))
        # # convert to np.float32
        Z = np.float32(Z)
        # define criteria, number of clusters(K) and apply kmeans()
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, num_iteractions, 1.0)
        ret, label, center = cv2.kmeans(Z, num_clusters, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
        # Now convert back into uint8, and make original image
        center = np.uint8(center)
        result = center[label.flatten()]
        result2 = result.reshape(image.shape)
        return result2


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


    def search_point(self, pos_x, pos_y):
        min_distance = 1e6
        distance = 0
        pos_min = -1
        x = 0
        y = 0

        for pos in range(len(self.project.coordinates_x)):
            x = self.project.coordinates_x[pos] - pos_x
            y = self.project.coordinates_y[pos] - pos_y
            distance = math.sqrt(x**2+y**2)
            if distance < min_distance:
                min_distance = distance
                pos_min = pos

        if min_distance > 50:
            pos_min = -1

        return pos_min

    def update_positions(self, x, y, mode, state):
        if mode == globals.GL_WIDGET_MODE_COPY_POSITION:
            if state == 0: # first point
                #search for the point in the list
                self.selected_point = self.search_point(x,y)
                if self.selected_point != -1:
                    self.selected_point_x = x
                    self.selected_point_y = y
                    # found -> update the texture
                    self.compute_positions_image()
                    # tell gl_widget that a first point was found
                    self.gl_widget.set_point_found(True)
            elif state == 1: #second point
                # and the two points to the list
                self.connected_points.append((self.project.coordinates_x[self.selected_point],
                                              self.project.coordinates_y[self.selected_point],
                                              x, y))
                # add the new position
                self.project.coordinates_x.append(x)
                self.project.coordinates_y.append(y)
                # add the estate for the new point. Value 2 implies that it is a copied point
                self.valid_positions=np.append(self.valid_positions,np.uint32(2))

                # all the elements must add a new position copying the values
                for key in self.project.xrf_data:
                    # get the value
                    value = self.project.xrf_data[key].values[self.selected_point]
                    self.project.xrf_data[key].values.append(value)
                # disable the selected point
                self.selected_point = -1
                # update texture
                self.compute_positions_image()
        elif mode == globals.GL_WIDGET_MODE_DELETE_POSITION:
            self.selected_point = self.search_point(x, y)
            if self.selected_point != -1:
                del self.project.coordinates_x[self.selected_point]
                del self.project.coordinates_y[self.selected_point]
                for key in self.project.xrf_data:
                    # get the value
                    del self.project.xrf_data[key].values[self.selected_point]
                # update texture
                self.selected_point = -1
                self.compute_positions_image()

