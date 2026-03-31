import sys
import os
from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QLineEdit, QFileDialog, 
                             QMessageBox, QInputDialog, QTabWidget, QMenu, QAction)
from PyQt5.QtWebEngineWidgets import QWebEngineView

class SoteBrowser(QMainWindow):
    def __init__(self, profile_name):
        super().__init__()
        self.profile_name = profile_name
        self.setWindowTitle(f'Sote Browser - {profile_name}')
        self.setGeometry(100, 100, 1280, 850)

        # Директории
        self.profile_dir = os.path.join(os.getcwd(), "profiles", profile_name)
        os.makedirs(self.profile_dir, exist_ok=True)
        self.settings_file = os.path.join(self.profile_dir, "home_page.txt")
        self.home_url = self.load_home_page()
        
        # Цвет темы по умолчанию
        self.accent_color = "#00ff41" 

        # Главный контейнер
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # --- ВЕРХНЯЯ ПАНЕЛЬ (Кнопки и URL) ---
        self.toolbar = QWidget()
        self.toolbar_layout = QHBoxLayout(self.toolbar)
        
        self.btn_back = QPushButton("⬅")
        self.btn_back.clicked.connect(lambda: self.current_browser().back())
        
        self.btn_reload = QPushButton("🔄")
        self.btn_reload.clicked.connect(lambda: self.current_browser().reload())

        self.url_input = QLineEdit()
        self.url_input.returnPressed.connect(self.load_url)

        self.btn_dl = QPushButton("📥")
        self.btn_dl.clicked.connect(lambda: QMessageBox.information(self, "Sote", "Скачивание начнется автоматически при клике по ссылке."))

        self.btn_menu = QPushButton("⚙️")
        self.btn_menu.setMenu(self.create_settings_menu())

        self.toolbar_layout.addWidget(self.btn_back)
        self.toolbar_layout.addWidget(self.btn_reload)
        self.toolbar_layout.addWidget(self.url_input)
        self.toolbar_layout.addWidget(self.btn_dl)
        self.toolbar_layout.addWidget(self.btn_menu)

        # --- ВКЛАДКИ ---
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.tab_changed)
        
        # Кнопка новой вкладки в углу панели вкладок
        self.add_tab_btn = QPushButton(" ➕ ")
        self.add_tab_btn.clicked.connect(lambda: self.add_new_tab(QUrl(self.home_url), "Новая вкладка"))
        self.tabs.setCornerWidget(self.add_tab_btn, Qt.TopRightCorner)

        # Собираем всё в главное окно
        self.main_layout.addWidget(self.tabs)
        self.main_layout.addWidget(self.toolbar) # Панель навигации теперь СНИЗУ или СВЕРХУ (как захочешь)

        self.update_ui_style()
        self.add_new_tab(QUrl(self.home_url), "Главная")

    def update_ui_style(self):
        style = f"""
            QMainWindow {{ background-color: #1a1a1a; }}
            QWidget {{ background-color: #1a1a1a; color: white; font-family: 'Segoe UI'; }}
            
            /* Стиль вкладок */
            QTabWidget::pane {{ border-top: 1px solid {self.accent_color}; }}
            QTabBar::tab {{
                background: #2b2b2b; color: #aaa; padding: 12px; min-width: 150px;
                border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 2px;
            }}
            QTabBar::tab:selected {{ background: #1a1a1a; color: {self.accent_color}; border-bottom: 2px solid {self.accent_color}; }}
            
            /* Стиль панели управления */
            QLineEdit {{ 
                background-color: #2b2b2b; border: 1px solid #444; padding: 6px; 
                border-radius: 12px; color: white; margin: 5px; 
            }}
            QPushButton {{ 
                background-color: #2b2b2b; border: 1px solid #444; 
                border-radius: 6px; padding: 5px; min-width: 35px; 
            }}
            QPushButton:hover {{ border-color: {self.accent_color}; color: {self.accent_color}; }}
        """
        self.setStyleSheet(style)

    def add_new_tab(self, qurl, label):
        browser = QWebEngineView()
        browser.setUrl(qurl)
        
        # Обработка заголовка вкладки
        browser.titleChanged.connect(lambda title: self.update_tab_title(browser, title))
        # Обработка скачивания
        browser.page().profile().downloadRequested.connect(self.handle_download)
        
        i = self.tabs.addTab(browser, label)
        self.tabs.setCurrentIndex(i)

    def update_tab_title(self, browser, title):
        index = self.tabs.indexOf(browser)
        if index != -1:
            self.tabs.setTabText(index, title[:15] + ".." if len(title) > 15 else title)

    def close_tab(self, i):
        if self.tabs.count() > 1:
            self.tabs.removeTab(i)
        else:
            self.current_browser().setUrl(QUrl(self.home_url))

    def tab_changed(self, i):
        if self.current_browser():
            url = self.current_browser().url().toString()
            self.url_input.setText(url)

    def current_browser(self):
        return self.tabs.currentWidget()

    def load_url(self):
        url = self.url_input.text()
        if url:
            if not url.startswith(('http://', 'https://')):
                url = 'http://' + url
            self.current_browser().setUrl(QUrl(url))

    def create_settings_menu(self):
        menu = QMenu(self)
        color_menu = menu.addMenu("🎨 Тема")
        for name, color in [("Зеленый", "#00ff41"), ("Синий", "#00aaff"), ("Красный", "#ff4444"), ("Золотой", "#ffcc00")]:
            act = QAction(name, self)
            act.triggered.connect(lambda checked, c=color: self.set_theme(c))
            color_menu.addAction(act)
        
        home_act = QAction("🏠 Сделать домашней", self)
        home_act.triggered.connect(self.set_home_page)
        menu.addAction(home_act)
        return menu

    def set_theme(self, color):
        self.accent_color = color
        self.update_ui_style()

    def set_home_page(self):
        url = self.current_browser().url().toString()
        with open(self.settings_file, "w") as f:
            f.write(url)
        self.home_url = url
        QMessageBox.information(self, "Sote", "Домашняя страница сохранена!")

    def load_home_page(self):
        return open(self.settings_file).read().strip() if os.path.exists(self.settings_file) else "https://www.google.com"

    def handle_download(self, download):
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить", download.suggestedFileName())
        if path:
            download.setPath(path); download.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    name, ok = QInputDialog.getText(None, "Профиль", "Имя:")
    if ok and name:
        window = SoteBrowser(name)
        window.show()
        sys.exit(app.exec_())