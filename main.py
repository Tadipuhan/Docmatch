import sys
from PySide6.QtWidgets import QApplication
from app import database, modern_data
from app.ui import Window


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('Manajemen Surat')
    database.migrate_legacy_data()
    database.initialize()
    modern_data.setup()
    window = Window()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
