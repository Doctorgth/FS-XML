DARK_STYLE = """
QMainWindow {
    border-image: url("images/background.png") 0 0 0 0 stretch stretch;
    background-color: #0b0f19;
    color: #f8fafc;
    font-family: 'Segoe UI', Arial, sans-serif;
}

QDialog {
    background-color: #0b0f19;
    color: #f8fafc;
    font-family: 'Segoe UI', Arial, sans-serif;
}

QWidget {
    color: #f8fafc;
    background-color: transparent;
}

QFrame#card {
    background-color: rgba(17, 24, 39, 0.45);
    border: 1px solid rgba(31, 41, 55, 0.3);
    border-radius: 8px;
}

QScrollArea, QScrollArea > QWidget > QWidget {
    background-color: transparent;
    border: none;
}

QLabel {
    color: #f8fafc;
    font-size: 13px;
}

QPushButton {
    background-color: rgba(30, 41, 59, 0.6);
    border: 1px solid rgba(51, 65, 85, 0.5);
    color: #f8fafc;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: rgba(51, 65, 85, 0.8);
    border-color: #475569;
}

QPushButton#btn_accent {
    background-color: rgba(2, 132, 199, 0.8);
    border: 1px solid #0369a1;
    color: #ffffff;
}

QPushButton#btn_accent:hover {
    background-color: #0ea5e9;
}

QPushButton#btn_danger {
    background-color: rgba(127, 29, 29, 0.8);
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
    background-color: rgba(51, 65, 85, 0.5);
    border-radius: 4px;
}

QTextEdit, QPlainTextEdit, QLineEdit {
    background-color: rgba(15, 23, 42, 0.3);
    border: 1px solid rgba(30, 41, 59, 0.3);
    border-radius: 6px;
    color: #f1f5f9;
    padding: 8px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 13px;
}

QTreeWidget, QListWidget {
    background-color: rgba(15, 23, 42, 0.3);
    border: 1px solid rgba(30, 41, 59, 0.3);
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