import os
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                               QPushButton, QListWidget, QListWidgetItem, QTextEdit,
                               QLabel, QFileDialog, QFrame, QScrollArea, QMessageBox, QSplitter)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor

from database import Database
from parser import XMLCodeParser
from executor import CodeExecutor
from ui.modals import InputModal, ContextFilePickerModal, AttachedFilesViewModal


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FS-XML Interpreter")
        self.resize(1350, 850)

        self.db = Database()
        self.executor = CodeExecutor(self.db)
        self.current_project_id = None

        self.init_ui()
        self.load_projects()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # --- ЛЕВАЯ ПАНЕЛЬ ---
        left_frame = QFrame()
        left_frame.setObjectName("card")
        left_frame.setMinimumWidth(200)
        left_layout = QVBoxLayout(left_frame)

        left_layout.addWidget(QLabel("<b>AI INTERPRETER</b>"))
        btn_new_proj = QPushButton("Новый проект")
        btn_new_proj.setObjectName("btn_accent")
        btn_new_proj.clicked.connect(self.create_project)
        left_layout.addWidget(btn_new_proj)

        left_layout.addWidget(QLabel("Проекты:"))
        self.project_list = QListWidget()
        self.project_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.project_list.itemClicked.connect(self.select_project)
        left_layout.addWidget(self.project_list)

        left_layout.addWidget(QLabel("Лог работы:"))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(160)
        left_layout.addWidget(self.log_text)

        # --- ЦЕНТРАЛЬНАЯ ПАНЕЛЬ ---
        center_frame = QFrame()
        center_frame.setObjectName("card")
        center_frame.setMinimumWidth(400)
        center_layout = QVBoxLayout(center_frame)

        # 1. Шапка центральной панели
        top_bar = QHBoxLayout()
        self.lbl_proj_name = QLabel("<b>Проект: -</b>")
        self.lbl_root_dir = QLabel("<b>Корневая директория проекта:</b> Не выбрана")
        btn_set_dir = QPushButton("Изменить директорию")
        btn_set_dir.clicked.connect(self.set_root_dir)

        top_bar.addWidget(self.lbl_proj_name)
        top_bar.addSpacing(15)
        top_bar.addWidget(self.lbl_root_dir)
        top_bar.addStretch()
        top_bar.addWidget(btn_set_dir)
        center_layout.addLayout(top_bar)

        # 2. Панель действий НАД окном ввода кода (как на чертеже)
        action_bar = QHBoxLayout()
        self.lbl_status = QLabel("")
        action_bar.addWidget(self.lbl_status)
        action_bar.addStretch()

        btn_clear = QPushButton("Очистить")
        btn_clear.clicked.connect(lambda: self.code_editor.clear())

        self.btn_run = QPushButton("ВЫПОЛНИТЬ ЗАМЕНУ")
        self.btn_run.setObjectName("btn_accent")
        self.btn_run.clicked.connect(self.run_execution)

        action_bar.addWidget(btn_clear)
        action_bar.addWidget(self.btn_run)
        center_layout.addLayout(action_bar)

        # 3. Редактор кода (занимает всё оставшееся пространство)
        self.code_editor = QTextEdit()
        self.code_editor.setPlaceholderText("Вставьте сюда XML-код замен от нейросети...")
        center_layout.addWidget(self.code_editor)

        # --- ПРАВАЯ ПАНЕЛЬ ---
        right_frame = QFrame()
        right_frame.setObjectName("card")
        right_frame.setMinimumWidth(250)
        right_layout = QVBoxLayout(right_frame)

        self.lbl_files_count = QLabel("ПРИКРЕПЛЕННЫЕ ФАЙЛЫ (0)")
        right_layout.addWidget(self.lbl_files_count)

        file_btns = QHBoxLayout()
        btn_edit_f = QPushButton("Редактировать")
        btn_edit_f.clicked.connect(self.open_file_picker)
        btn_view_f = QPushButton("Просмотр")
        btn_view_f.clicked.connect(self.open_file_viewer)
        file_btns.addWidget(btn_edit_f)
        file_btns.addWidget(btn_view_f)
        right_layout.addLayout(file_btns)

        right_layout.addWidget(QLabel("<b>ИСТОРИЯ ЗАПУСКОВ (ОТКАТ)</b>"))

        self.history_scroll = QScrollArea()
        self.history_scroll.setWidgetResizable(True)
        self.history_widget = QWidget()
        self.history_layout = QVBoxLayout(self.history_widget)
        self.history_layout.setAlignment(Qt.AlignTop)
        self.history_scroll.setWidget(self.history_widget)
        right_layout.addWidget(self.history_scroll)

        btn_dump = QPushButton("СОЗДАТЬ ДАМП КОНТЕКСТА")
        btn_dump.setObjectName("btn_accent")
        btn_dump.clicked.connect(self.make_dump)
        right_layout.addWidget(btn_dump)

        # Кнопка очистки БД в самом низу панели
        btn_clear_hist = QPushButton("Очистить историю сессий")
        btn_clear_hist.setObjectName("btn_danger")
        btn_clear_hist.clicked.connect(self.clear_history)
        right_layout.addWidget(btn_clear_hist)

        # Сборка через перетаскиваемый QSplitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_frame)
        splitter.addWidget(center_frame)
        splitter.addWidget(right_frame)
        splitter.setSizes([260, 650, 380])

        main_layout.addWidget(splitter)

    def log(self, msg):
        self.log_text.append(msg)

    # --- Проекты ---
    def load_projects(self):
        self.project_list.clear()
        projects = self.db.get_projects()
        for p_id, name, r_dir in projects:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, (p_id, name, r_dir))
            item.setSizeHint(QSize(0, 36))

            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(6, 2, 6, 2)
            layout.setSpacing(6)

            lbl = QLabel(name)
            lbl.setStyleSheet("font-size: 13px; color: #f8fafc; font-weight: 500;")

            btn_edit = QPushButton("✎")
            btn_edit.setFixedSize(24, 24)
            btn_edit.setToolTip("Переименовать")
            btn_edit.setStyleSheet("""
                                    QPushButton {
                                        border: 1px solid #334155;
                                        border-radius: 4px;
                                        background-color: #1e293b;
                                        color: #38bdf8;
                                        font-size: 13px;
                                        font-weight: bold;
                                        padding: 0px;
                                        margin: 0px;
                                    }
                                    QPushButton:hover {
                                        background-color: #0284c7;
                                        color: #ffffff;
                                    }
                                """)
            btn_edit.clicked.connect(lambda _, pid=p_id, n=name: self.rename_project(pid, n))

            btn_del = QPushButton("✕")
            btn_del.setFixedSize(24, 24)
            btn_del.setToolTip("Удалить")
            btn_del.setStyleSheet("""
                                    QPushButton {
                                        border: 1px solid #334155;
                                        border-radius: 4px;
                                        background-color: #1e293b;
                                        color: #ef4444;
                                        font-size: 13px;
                                        font-weight: bold;
                                        padding: 0px;
                                        margin: 0px;
                                    }
                                    QPushButton:hover {
                                        background-color: #dc2626;
                                        color: #ffffff;
                                    }
                                """)
            btn_del.clicked.connect(lambda _, pid=p_id, n=name: self.delete_project(pid, n))

            layout.addWidget(lbl, stretch=1)
            layout.addWidget(btn_edit)
            layout.addWidget(btn_del)

            self.project_list.addItem(item)
            self.project_list.setItemWidget(item, widget)

    def create_project(self):
        dlg = InputModal("Новый проект", "Введите название проекта:", "New Project")
        if dlg.exec():
            name = dlg.get_value()
            if name:
                root_dir = os.getcwd()
                self.db.add_project(name, root_dir)
                self.load_projects()

    def select_project(self, item):
        p_id, name, r_dir = item.data(Qt.UserRole)
        self.current_project_id = p_id
        self.lbl_proj_name.setText(f"<b>Проект:</b> {name}")
        self.lbl_root_dir.setText(f"<b>Корневая директория проекта:</b> {r_dir}")
        self.update_files_count()
        self.load_history()

    def rename_project(self, p_id, current_name):
        dlg = InputModal("Переименование", "Новое имя:", current_name)
        if dlg.exec():
            new_name = dlg.get_value()
            if new_name:
                self.db.update_project(p_id, name=new_name)
                self.load_projects()

    def delete_project(self, p_id, p_name=""):
        reply = QMessageBox.question(
            self,
            "Удаление проекта",
            f"Вы уверены, что хотите удалить проект '{p_name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.db.delete_project(p_id)
            if self.current_project_id == p_id:
                self.current_project_id = None
                self.lbl_proj_name.setText("<b>Проект:</b> -")
                self.lbl_root_dir.setText("<b>Корневая директория проекта:</b> Не выбрана")
            self.load_projects()

    def set_root_dir(self):
        if not self.current_project_id: return
        dir_path = QFileDialog.getExistingDirectory(self, "Выберите корневую папку")
        if dir_path:
            self.db.update_project(self.current_project_id, root_dir=dir_path)
            self.lbl_root_dir.setText(f"<b>Корневая директория проекта:</b> {dir_path}")
            self.load_projects()

    # --- Файлы ---
    def update_files_count(self):
        files = self.db.get_project_files(self.current_project_id)
        self.lbl_files_count.setText(f"ПРИКРЕПЛЕННЫЕ ФАЙЛЫ ({len(files)})")

    def open_file_picker(self):
        if not self.current_project_id: return
        r_dir = self.get_current_root_dir()
        curr_files = self.db.get_project_files(self.current_project_id)
        dlg = ContextFilePickerModal(r_dir, curr_files)
        if dlg.exec():
            selected = dlg.get_selected_files()
            self.db.set_project_files(self.current_project_id, selected)
            self.update_files_count()

    def open_file_viewer(self):
        if not self.current_project_id: return
        curr_files = self.db.get_project_files(self.current_project_id)
        dlg = AttachedFilesViewModal(curr_files)
        if dlg.exec():
            self.db.set_project_files(self.current_project_id, dlg.get_files())
            self.update_files_count()

    def get_current_root_dir(self):
        for i in range(self.project_list.count()):
            item = self.project_list.item(i)
            p_id, name, r_dir = item.data(Qt.UserRole)
            if p_id == self.current_project_id:
                return r_dir
        return os.getcwd()

    # --- Исполнение ---
    def run_execution(self):
        if not self.current_project_id:
            self.log("Ошибка: Сначала выберите проект.")
            return

        xml_raw = self.code_editor.toPlainText()
        instructions = XMLCodeParser.parse(xml_raw)

        if not instructions:
            self.log("XML парсер не нашел валидных тегов замены.")
            return

        r_dir = self.get_current_root_dir()
        success = self.executor.execute_session(self.current_project_id, r_dir, instructions, self.log)

        if success:
            self.lbl_status.setText("<b style='color:#22c55e;'>УСПЕШНО ПРИМЕНЕНО</b>")
        else:
            self.lbl_status.setText("<b style='color:#ef4444;'>ОШИБКА ПРИМЕНЕНИЯ</b>")

        self.load_history()

    def load_history(self):
        # Корректное удаление элементов из Qt Layout
        while self.history_layout.count():
            item = self.history_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.current_project_id: return

        executions = self.db.get_executions(self.current_project_id)
        for ex in executions:
            box = QFrame()
            box.setObjectName("card")
            box_layout = QVBoxLayout(box)

            header = QLabel(f"<b>Сессия: {ex['timestamp']}</b>")
            box_layout.addWidget(header)

            for ch in ex['changes']:
                ch_id, file_path, c_type, s_c, r_c, snap, st, err = ch
                snippet = "\n".join((r_c or "").splitlines()[:3])

                # Цвет статуса
                color = "#22c55e" if st == "Success" else "#eab308" if st == "RolledBack" else "#ef4444"
                ch_lbl = QLabel(f"📄 <b>{file_path}</b> [<span style='color:{color};'>{st}</span>]\n<span style='color:#64748b;'>{snippet}</span>")
                box_layout.addWidget(ch_lbl)

                # Вывод сообщения об ошибке
                if err:
                    err_lbl = QLabel(f"<span style='color:#ef4444; font-size: 11px;'>⚠️ {err}</span>")
                    err_lbl.setWordWrap(True)
                    box_layout.addWidget(err_lbl)

                # Кнопка Отката
                if st == 'Success':
                    btn_undo = QPushButton("Откатить")
                    btn_undo.setObjectName("btn_danger")
                    btn_undo.clicked.connect(lambda checked, cid=ch_id: self.undo_change(cid))
                    box_layout.addWidget(btn_undo)
                # Кнопка повторного Применения после отката
                elif st == 'RolledBack':
                    btn_reapply = QPushButton("Применить снова")
                    btn_reapply.setObjectName("btn_accent")
                    btn_reapply.clicked.connect(lambda checked, cid=ch_id: self.reapply_change(cid))
                    box_layout.addWidget(btn_reapply)

            self.history_layout.addWidget(box)

    def undo_change(self, change_id):
        r_dir = self.get_current_root_dir()

        # Проверка на ручные изменения файла после сессии
        if self.executor.is_modified_manually(change_id, r_dir):
            reply = QMessageBox.question(
                self,
                "Внимание! Файл изменен",
                "Внимание! Файл был изменен вручную после этой сессии.\nОткат затрет ваши ручные изменения. Продолжить?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        ok, msg = self.executor.rollback_change(change_id, r_dir)
        self.log(f"Откат: {msg}")
        self.load_history()

    def clear_history(self):
        if not self.current_project_id:
            return

        reply = QMessageBox.question(
            self,
            "Очистка истории",
            "Вы уверены, что хотите полностью очистить историю сессий?\nЭто освободит место в БД, но откатить прошлые изменения станет невозможно.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.db.clear_project_history(self.current_project_id)
            self.load_history()
            self.log("История сессий очищена, база данных сжата.")

    def reapply_change(self, change_id):
        r_dir = self.get_current_root_dir()
        ok, msg = self.executor.reapply_change(change_id, r_dir)
        self.log(f"Повторное применение: {msg}")
        self.load_history()

    def make_dump(self):
        if not self.current_project_id: return
        r_dir = self.get_current_root_dir()
        ok, res = self.executor.generate_dump(self.current_project_id, r_dir)
        if ok:
            self.log(f"Дамп сохранен: {res}")
            QMessageBox.information(self, "Дамп сохранен", f"Файл:\n{res}")
        else:
            self.log(f"Ошибка дампа: {res}")