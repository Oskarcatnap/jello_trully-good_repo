import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QFileSystemModel, 
                             QTreeView, QVBoxLayout, QWidget, QHBoxLayout, 
                             QPushButton, QInputDialog, QMessageBox, QFrame)
from PyQt5.QtCore import QDir, QSize, Qt

class SoteFileManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SOTE OS - FILE SYSTEM")
        self.setGeometry(200, 200, 1000, 700)

        # --- СТИЛЬ SOTE OS ---
        self.setStyleSheet("""
            QMainWindow { background-color: #121212; }
            QWidget { background-color: #121212; color: #00ff41; font-family: 'Consolas', monospace; }
            
            QTreeView { 
                background-color: #181818; border: 1px solid #00ff41; 
                gridline-color: #333; font-size: 14px; outline: 0;
            }
            QTreeView::item:hover { background: #1e1e1e; }
            QTreeView::item:selected { background: #00ff41; color: black; }

            QPushButton { 
                background-color: #181818; border: 1px solid #00ff41; 
                padding: 8px; border-radius: 4px; min-width: 80px;
            }
            QPushButton:hover { background-color: #00ff41; color: black; }
            
            QFrame#Sidebar { border-right: 1px solid #333; background-color: #0d0d0d; }
        """)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)

        # --- БОКОВАЯ ПАНЕЛЬ (SIDEBAR) ---
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(180)
        self.side_layout = QVBoxLayout(self.sidebar)
        
        self.add_side_btn("🏠 Home", QDir.homePath())
        self.add_side_btn("📄 Desktop", os.path.join(os.path.expanduser("~"), "Desktop"))
        self.add_side_btn("📥 Downloads", os.path.join(os.path.expanduser("~"), "Downloads"))
        self.add_side_btn("💾 Root (C:)", QDir.rootPath())
        self.side_layout.addStretch() # Прижимает кнопки к верху

        # --- ОСНОВНАЯ ЧАСТЬ ---
        self.content_layout = QVBoxLayout()
        
        # Верхние кнопки управления
        self.top_bar = QHBoxLayout()
        self.btn_back = QPushButton("⬅ Back")
        self.btn_back.clicked.connect(self.go_up)
        
        self.btn_new_folder = QPushButton("➕ New Folder")
        self.btn_new_folder.clicked.connect(self.make_folder)
        
        self.btn_delete = QPushButton("🗑 Delete")
        self.btn_delete.clicked.connect(self.delete_item)

        self.top_bar.addWidget(self.btn_back)
        self.top_bar.addWidget(self.btn_new_folder)
        self.top_bar.addStretch()
        self.top_bar.addWidget(self.btn_delete)

        # Модель и Дерево файлов
        self.model = QFileSystemModel()
        self.model.setRootPath("") 
        
        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(QDir.homePath()))
        self.tree.setColumnWidth(0, 400)
        self.tree.setSortingEnabled(True)
        self.tree.doubleClicked.connect(self.on_double_click)

        self.content_layout.addLayout(self.top_bar)
        self.content_layout.addWidget(self.tree)

        self.main_layout.addWidget(self.sidebar)
        self.main_layout.addLayout(self.content_layout)

    def add_side_btn(self, name, path):
        btn = QPushButton(name)
        btn.clicked.connect(lambda: self.tree.setRootIndex(self.model.index(path)))
        self.side_layout.addWidget(btn)

    def on_double_click(self, index):
        file_path = self.model.filePath(index)
        if os.path.isdir(file_path):
            self.tree.setRootIndex(index)
        else:
            os.startfile(file_path) # Открыть файл в системе

    def go_up(self):
        current_index = self.tree.rootIndex()
        parent_index = current_index.parent()
        if parent_index.isValid():
            self.tree.setRootIndex(parent_index)

    def make_folder(self):
        index = self.tree.rootIndex()
        path = self.model.filePath(index)
        name, ok = QInputDialog.getText(self, "New Folder", "Enter folder name:")
        if ok and name:
            os.mkdir(os.path.join(path, name))

    def delete_item(self):
        index = self.tree.currentIndex()
        if not index.isValid(): return
        
        path = self.model.filePath(index)
        confirm = QMessageBox.question(self, "Delete", f"Are you sure you want to delete {os.path.basename(path)}?", 
                                       QMessageBox.Yes | QMessageBox.No)
        
        if confirm == QMessageBox.Yes:
            if os.path.isdir(path):
                os.rmdir(path) # Только для пустых папок (безопасно)
            else:
                os.remove(path)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = SoteFileManager()
    window.show()
    sys.exit(app.exec_())