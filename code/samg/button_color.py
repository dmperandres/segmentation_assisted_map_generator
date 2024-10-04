import sys
from PySide6.QtCore import Qt, Slot, QDir, QSize, Signal
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtGui import QMatrix4x4, QAction, QPixmap, QIcon, QFontMetrics, QFont, QColor, QPainter, QMouseEvent, QPen
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


class button_color(QWidget):

    colorChanged = Signal(QColor)

    def __init__(self, initial_color=QColor("blue")):
        super().__init__()
        self.color = initial_color
        self.setFixedSize(20, 20)  # Tamaño fijo del widget

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setBrush(self.color)
        painter.setPen(QPen(Qt.black, 1))
        rect = self.rect().adjusted(1, 1, -1, -1)  # Ajustar para el borde
        painter.drawRect(rect)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            new_color = QColorDialog.getColor(self.color, self, "Select Color")
            if new_color.isValid():
                self.color = new_color
                self.update()  # Actualizar el widget para mostrar el nuevo color
                self.colorChanged.emit(self.color)