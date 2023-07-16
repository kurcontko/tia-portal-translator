# gui/app.py
from PyQt5.QtWidgets import QFileDialog, QVBoxLayout, QPushButton, QWidget
from core.translator import translate_excel

class App(QWidget):
    def __init__(self):
        super().__init__()

        self.title = 'Translator'
        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.title)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.btn_select_file = QPushButton('Select Excel File', self)
        self.btn_select_file.clicked.connect(self.open_file_name_dialog)
        layout.addWidget(self.btn_select_file)

        self.btn_translate = QPushButton('Translate', self)
        self.btn_translate.clicked.connect(self.translate_file)
        layout.addWidget(self.btn_translate)

    def open_file_name_dialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        file_name, _ = QFileDialog.getOpenFileName(self,"Select Excel File", "", "Excel Files (*.xlsx)", options=options)
        if file_name:
            print(file_name)
            self.file_path = file_name

    def translate_file(self):
        if self.file_path is not None:
            translate_excel(self.file_path)
