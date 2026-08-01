DARK_STYLE = """
QMainWindow, QDialog {
    background-color: #0b0f19;
    color: #f8fafc;
    font-family: 'Segoe UI', Arial, sans-serif;
}

QWidget {
    color: #f8fafc;
    background-color: transparent;
}

QFrame#card {
    background-color: #111827;
    border: 1px solid #1f2937;
    border-radius: 8px;
}

QScrollArea, QScrollArea > QWidget > QWidget {
    background-color: #0b0f19;
    border: none;
}

QLabel {
    color: #f8fafc;
    font-size: 13px;
}

QPushButton {
    background-color: #1e293b;
    border: 1px solid #334155;
    color: #f8fafc;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #334155;
    border-color: #475569;
}

QPushButton#btn_accent {
    background-color: #0284c7;
    border: 1px solid #0369a1;
    color: #ffffff;
}

QPushButton#btn_accent:hover {
    background-color: #0ea5e9;
}

QPushButton#btn_danger {
    background-color: #7f1d1d;
    border: 1px solid #991b1b;
    color: #ffffff;
}

QPushButton#btn_danger:hover {
    background-color: #dc2626;
}

QPushButton#btn_icon {
    background-color: transparent;
    border: none;
    padding: 2px 4px;
    font-size: 12px;
}

QPushButton#btn_icon:hover {
    background-color: #334155;
    border-radius: 4px;
}

QTextEdit, QPlainTextEdit, QLineEdit {
    background-color: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 6px;
    color: #f1f5f9;
    padding: 8px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 13px;
}

QTreeWidget, QListWidget {
    background-color: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 6px;
    color: #f1f5f9;
    padding: 4px;
    outline: none;
}

QTreeWidget::item, QListWidget::item {
    padding: 4px;
    border-radius: 4px;
    border: none;
    outline: none;
}

QTreeWidget::item:hover, QListWidget::item:hover {
    background-color: #1e293b;
}

QTreeWidget::item:selected, QTreeWidget::item:focus, QListWidget::item:focus {
    background-color: #1e293b;
    border: none;
    outline: none;
}

QHeaderView::section {
    background-color: #1e293b;
    color: #f8fafc;
    padding: 6px;
    border: none;
    font-weight: bold;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #475569;
    background-color: #0f172a;
}

QCheckBox::indicator:checked {
    background-color: #0284c7;
    border-color: #38bdf8;
}

QSplitter::handle {
    background-color: #1e293b;
    width: 6px;
    margin: 2px;
    border-radius: 3px;
}

QSplitter::handle:hover {
    background-color: #0284c7;
}
"""