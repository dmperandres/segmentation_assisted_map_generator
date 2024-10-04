from PySide6.QtWidgets import QApplication
import window
import sys

if __name__ == '__main__':
    if sys.prefix != sys.base_prefix:
        print("Running on a virtual enviroment")
    app = QApplication(sys.argv)
    window = window.main_window()
    window.show()
    sys.exit(app.exec())
