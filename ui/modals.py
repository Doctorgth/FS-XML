import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget,
                               QTreeWidgetItem, QPushButton, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QCheckBox, QWidget)
from PySide6.QtCore import Qt, QSignalBlocker
from PySide6.QtGui import QColor


class InputModal(QDialog):
    def __init__(self, title, label_text, default_val=""):
        super().__init__()
        self.setWindowTitle(title)
        self.setFixedWidth(350)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(label_text))
        self.input = QLineEdit(default_val)
        layout.addWidget(self.input)

        btn_box = QHBoxLayout()
        btn_ok = QPushButton("ОК")
        btn_ok.setObjectName("btn_accent")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)

        btn_box.addWidget(btn_ok)
        btn_box.addWidget(btn_cancel)
        layout.addLayout(btn_box)

    def get_value(self):
        return self.input.text().strip()


class ContextFilePickerModal(QDialog):
    def __init__(self, root_dir, current_files):
        super().__init__()
        self.setWindowTitle("ВЫБОР ФАЙЛОВ КОНТЕКСТА")
        self.resize(680, 650)
        self.root_dir = root_dir
        # dict: rel_path -> 0 (Writable) or 1 (Read-Only)
        self.file_states = {rel: is_ro for rel, is_ro in current_files}

        layout = QVBoxLayout(self)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Файлы и папки", "Writable (W)", "Read-Only (RO)"])
        self.tree.setColumnWidth(0, 400)
        self.tree.setColumnWidth(1, 110)
        self.tree.setColumnWidth(2, 110)
        layout.addWidget(self.tree)

        self.populate_tree()

        bottom_bar = QHBoxLayout()
        self.lbl_count = QLabel("Выбрано элементов: 0")
        self.lbl_count.setStyleSheet("font-weight: bold; color: #38bdf8;")

        btn_reset = QPushButton("Сбросить")
        btn_reset.clicked.connect(self.reset_selection)

        btn_confirm = QPushButton("Подтвердить")
        btn_confirm.setObjectName("btn_accent")
        btn_confirm.clicked.connect(self.accept)

        bottom_bar.addWidget(self.lbl_count)
        bottom_bar.addStretch()
        bottom_bar.addWidget(btn_reset)
        bottom_bar.addWidget(btn_confirm)
        layout.addLayout(bottom_bar)

        self.update_count_label()

    def populate_tree(self):
        self.tree.clear()
        root_item = QTreeWidgetItem(self.tree, [os.path.basename(self.root_dir)])
        root_item.setData(0, Qt.UserRole, "")
        self.add_checkboxes(root_item, rel_path="")
        self.build_branch(self.root_dir, root_item)
        self.tree.expandItem(root_item)

    def build_branch(self, current_dir, parent_item):
        try:
            entries = sorted(os.listdir(current_dir))
        except PermissionError:
            return

        for entry in entries:
            if entry.startswith('.') or entry == '__pycache__':
                continue
            full_path = os.path.join(current_dir, entry)
            rel_path = os.path.relpath(full_path, self.root_dir)
            is_dir = os.path.isdir(full_path)

            icon = "📁 " if is_dir else "📄 "
            item = QTreeWidgetItem(parent_item, [f"{icon}{entry}"])
            item.setData(0, Qt.UserRole, rel_path)

            self.add_checkboxes(item, rel_path)

            if is_dir:
                self.build_branch(full_path, item)

    def add_checkboxes(self, item, rel_path):
        cb_w = QCheckBox()
        cb_ro = QCheckBox()

        if rel_path in self.file_states:
            state = self.file_states[rel_path]
            if state == 0:
                cb_w.setChecked(True)
                item.setForeground(0, QColor("#22c55e"))
            else:
                cb_ro.setChecked(True)
                item.setForeground(0, QColor("#eab308"))

        cb_w.clicked.connect(lambda ch, it=item: self.on_cb_clicked(it, 'w', ch))
        cb_ro.clicked.connect(lambda ch, it=item: self.on_cb_clicked(it, 'ro', ch))

        self.tree.setItemWidget(item, 1, cb_w)
        self.tree.setItemWidget(item, 2, cb_ro)

    def on_cb_clicked(self, item, mode, is_checked):
        target_state = mode if is_checked else None

        # Рекурсивно применяем ко всем вложенным элементам
        self.apply_recursive(item, target_state)

        # Сбрасываем галочки у всех родителей (так как структура изменилась)
        self.reset_parents(item)

        self.update_count_label()

    def set_item_state(self, item, state_type):
        # state_type: 'w', 'ro', or None
        cb_w = self.tree.itemWidget(item, 1)
        cb_ro = self.tree.itemWidget(item, 2)
        rel_path = item.data(0, Qt.UserRole)

        if not cb_w or not cb_ro: return

        with QSignalBlocker(cb_w), QSignalBlocker(cb_ro):
            if state_type == 'w':
                cb_w.setChecked(True)
                cb_ro.setChecked(False)
                item.setForeground(0, QColor("#22c55e"))
                if rel_path: self.file_states[rel_path] = 0
            elif state_type == 'ro':
                cb_w.setChecked(False)
                cb_ro.setChecked(True)
                item.setForeground(0, QColor("#eab308"))
                if rel_path: self.file_states[rel_path] = 1
            else:
                cb_w.setChecked(False)
                cb_ro.setChecked(False)
                item.setForeground(0, QColor("#f8fafc"))
                if rel_path in self.file_states:
                    del self.file_states[rel_path]

    def apply_recursive(self, item, state_type):
        self.set_item_state(item, state_type)
        for i in range(item.childCount()):
            self.apply_recursive(item.child(i), state_type)

    def reset_parents(self, item):
        parent = item.parent()
        while parent:
            cb_w = self.tree.itemWidget(parent, 1)
            cb_ro = self.tree.itemWidget(parent, 2)
            if cb_w and cb_ro:
                with QSignalBlocker(cb_w), QSignalBlocker(cb_ro):
                    cb_w.setChecked(False)
                    cb_ro.setChecked(False)
                parent.setForeground(0, QColor("#f8fafc"))
                parent_rel = parent.data(0, Qt.UserRole)
                if parent_rel in self.file_states:
                    del self.file_states[parent_rel]
            parent = parent.parent()

    def reset_selection(self):
        self.file_states.clear()
        self.populate_tree()
        self.update_count_label()

    def update_count_label(self):
        self.lbl_count.setText(f"Выбрано элементов: {len(self.file_states)}")

    def get_selected_files(self):
        return [(rel, is_ro) for rel, is_ro in self.file_states.items()]


class AttachedFilesViewModal(QDialog):
    def __init__(self, current_files):
        super().__init__()
        self.setWindowTitle("ПРИКРЕПЛЕННЫЕ ФАЙЛЫ")
        self.resize(550, 450)
        self.file_states = dict(current_files)

        layout = QVBoxLayout(self)
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        self.refresh_list()

        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def refresh_list(self):
        self.list_widget.clear()
        for rel_path, is_ro in list(self.file_states.items()):
            item = QListWidgetItem()
            widget = QWidget()
            row_layout = QHBoxLayout(widget)
            row_layout.setContentsMargins(4, 2, 4, 2)

            lbl_name = QLabel(rel_path)
            btn_status = QPushButton("[READ_ONLY]" if is_ro == 1 else "[WRITABLE]")
            btn_status.setStyleSheet("color: #eab308;" if is_ro == 1 else "color: #22c55e;")
            btn_status.clicked.connect(lambda _, r=rel_path: self.toggle_status(r))

            btn_del = QPushButton("🗑️")
            btn_del.setObjectName("btn_icon")
            btn_del.clicked.connect(lambda _, r=rel_path: self.remove_file(r))

            row_layout.addWidget(lbl_name)
            row_layout.addStretch()
            row_layout.addWidget(btn_status)
            row_layout.addWidget(btn_del)

            item.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)

    def toggle_status(self, rel_path):
        self.file_states[rel_path] = 0 if self.file_states[rel_path] == 1 else 1
        self.refresh_list()

    def remove_file(self, rel_path):
        if rel_path in self.file_states:
            del self.file_states[rel_path]
            self.refresh_list()

    def get_files(self):
        return list(self.file_states.items())