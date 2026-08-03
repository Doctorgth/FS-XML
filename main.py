import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from ui.theme import DARK_STYLE

# --- ДОБАВИТЬ ЭТОТ БЛОК ДЛЯ ОТОБРАЖЕНИЯ ИКОНКИ НА ПАНЕЛИ ЗАДАЧ WINDOWS ---
if sys.platform == 'win32':
    import ctypes
    # Указываем Windows уникальный идентификатор нашего приложения (AppID)
    myappid = 'mycompany.xmlexecutor.app.1.0'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
# ------------------------------------------------------------------------


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLE)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()