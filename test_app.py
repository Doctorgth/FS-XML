import os
import textwrap
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox, QFileDialog, QPushButton

from database import Database
from parser import XMLCodeParser
from executor import CodeExecutor
from ui.main_window import MainWindow
from ui.modals import InputModal, ContextFilePickerModal, AttachedFilesViewModal


# ==========================================
# ФИКСТУРЫ ДЛЯ БЭКЕНДА И GUI
# ==========================================
@pytest.fixture
def test_env(tmp_path):
    """Изолированное окружение для бэкенд тестов."""
    db_file = tmp_path / "backend_test.db"
    db = Database(db_path=str(db_file))
    executor = CodeExecutor(db)
    project_id = db.add_project("Backend Project", str(tmp_path))
    return {
        "db": db,
        "executor": executor,
        "project_id": project_id,
        "root_dir": str(tmp_path)
    }


@pytest.fixture
def gui_window(qtbot, tmp_path):
    """Изолированное GUI окно с подмененной тестовой БД."""
    db_file = tmp_path / "gui_e2e_test.db"
    test_db = Database(db_path=str(db_file))

    window = MainWindow()
    window.db = test_db
    window.executor = CodeExecutor(test_db)
    qtbot.addWidget(window)
    return window, test_db, str(tmp_path)


# ==========================================
# 1. ТЕСТЫ БЭКЕНДА (БД, ПАРСЕР, EXECUTOR)
# ==========================================
def test_database_project_crud(test_env):
    db = test_env["db"]
    p_id = test_env["project_id"]

    assert len(db.get_projects()) == 1
    db.update_project(p_id, name="Renamed")
    assert db.get_projects()[0][1] == "Renamed"
    db.delete_project(p_id)
    assert len(db.get_projects()) == 0


def test_database_clear_history(test_env):
    db = test_env["db"]
    p_id = test_env["project_id"]
    exec_id = db.create_execution(p_id)
    db.add_change(exec_id, "file.py", "create", "", "print(1)", None, "Success")

    assert len(db.get_executions(p_id)) == 1
    db.clear_project_history(p_id)
    assert len(db.get_executions(p_id)) == 0


def test_xml_parser_create_and_edit():
    raw_xml = textwrap.dedent("""\
        <fs_create path="main.py">
        print("Hello World")
        </fs_create>

        <fs_edit path="config.py">
            <fs_search>DEBUG = False</fs_search>
            <fs_replace>DEBUG = True</fs_replace>
        </fs_edit>

        <fs_edit path="all_file.py">
            <fs_search><all/></fs_search>
            <fs_replace>NEW ALL CONTENT</fs_replace>
        </fs_edit>
    """)

    instructions = XMLCodeParser.parse(raw_xml)
    assert len(instructions) == 3
    assert instructions[0]['type'] == 'create'
    assert instructions[0]['path'] == 'main.py'
    assert instructions[0]['content'] == 'print("Hello World")'
    assert instructions[1]['type'] == 'edit'
    assert instructions[1]['replace_all'] is False
    assert instructions[2]['replace_all'] is True


def test_executor_file_creation(test_env):
    executor = test_env["executor"]
    p_id = test_env["project_id"]
    r_dir = test_env["root_dir"]

    instructions = [{'type': 'create', 'path': 'app/main.py', 'content': 'print("OK")'}]
    assert executor.execute_session(p_id, r_dir, instructions) is True

    created_file = os.path.join(r_dir, 'app', 'main.py')
    assert os.path.exists(created_file)


def test_executor_readonly_protection(test_env):
    db, executor, p_id, r_dir = test_env["db"], test_env["executor"], test_env["project_id"], test_env["root_dir"]
    file_path = os.path.join(r_dir, "readonly.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("Original")

    db.set_project_files(p_id, [("readonly.txt", 1)])
    instructions = [{'type': 'edit', 'path': 'readonly.txt', 'search': 'Original', 'replace': 'Hack', 'replace_all': False}]

    assert executor.execute_session(p_id, r_dir, instructions) is False
    with open(file_path, 'r', encoding='utf-8') as f:
        assert f.read() == "Original"


def test_manual_modification_detection_and_rollback(test_env):
    db, executor, p_id, r_dir = test_env["db"], test_env["executor"], test_env["project_id"], test_env["root_dir"]

    executor.execute_session(p_id, r_dir, [{'type': 'create', 'path': 'code.py', 'content': 'A = 10'}])
    executor.execute_session(p_id, r_dir, [{'type': 'edit', 'path': 'code.py', 'search': 'A = 10', 'replace': 'A = 20', 'replace_all': False}])

    execs = db.get_executions(p_id)
    last_change_id = execs[0]['changes'][0][0]

    assert executor.is_modified_manually(last_change_id, r_dir) is False

    file_abs = os.path.join(r_dir, 'code.py')
    with open(file_abs, 'w', encoding='utf-8') as f:
        f.write('A = 20\n# MANUAL')

    assert executor.is_modified_manually(last_change_id, r_dir) is True

    ok, _ = executor.rollback_change(last_change_id, r_dir)
    assert ok is True
    with open(file_abs, 'r', encoding='utf-8') as f:
        assert f.read() == 'A = 10'


def test_context_dump_generation(test_env):
    db, executor, p_id, r_dir = test_env["db"], test_env["executor"], test_env["project_id"], test_env["root_dir"]
    file_path = os.path.join(r_dir, "test.py")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("print('Dump Test')")

    db.set_project_files(p_id, [("test.py", 0)])
    ok, dump_path = executor.generate_dump(p_id, r_dir)
    assert ok is True
    assert os.path.exists(dump_path)


# ==========================================
# 2. ПОЛНЫЕ E2E ТЕСТЫ ИНТЕРФЕЙСА (GUI)
# ==========================================

def test_gui_e2e_project_lifecycle(qtbot, gui_window, monkeypatch):
    """E2E: Создание, выбор, переименование, смена директории и удаление проекта."""
    window, db, root_dir = gui_window

    # 1. Тест кнопки "Новый проект" с моком диалога ввода
    monkeypatch.setattr(InputModal, "exec", lambda self: True)
    monkeypatch.setattr(InputModal, "get_value", lambda self: "New E2E Project")

    # Имитируем клик по кнопке "Новый проект"
    window.create_project()
    assert window.project_list.count() == 1

    # 2. Выбор проекта
    item = window.project_list.item(0)
    window.select_project(item)
    assert "New E2E Project" in window.lbl_proj_name.text()

    # 3. Переименование проекта
    p_id = window.current_project_id
    monkeypatch.setattr(InputModal, "get_value", lambda self: "Renamed E2E Project")
    window.rename_project(p_id, "New E2E Project")
    assert "Renamed E2E Project" in window.project_list.itemWidget(window.project_list.item(0)).findChild(
        type(window.lbl_proj_name)).text()

    # 4. Смена корневой директории
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *args: root_dir)
    window.set_root_dir()
    assert root_dir in window.lbl_root_dir.text()

    # 5. Удаление проекта с моком подтверждения QMessageBox
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.Yes)
    window.delete_project(p_id, "Renamed E2E Project")
    assert window.project_list.count() == 0


def test_gui_e2e_execution_and_history_widgets(qtbot, gui_window, monkeypatch):
    """E2E: Выполнение замен из окна ввода, карточки истории, кнопки Отката и Применения."""
    window, db, root_dir = gui_window

    # Создаем проект
    p_id = db.add_project("Exec Project", root_dir)
    window.load_projects()
    window.select_project(window.project_list.item(0))

    # Вставляем XML с убранными отступами через dedent
    xml_code = textwrap.dedent("""\
        <fs_create path="gui_file.py">
        x = 100
        </fs_create>
    """)
    window.code_editor.setPlainText(xml_code)

    # Нажимаем "ВЫПОЛНИТЬ ЗАМЕНУ"
    qtbot.mouseClick(window.btn_run, Qt.LeftButton)

    # Проверяем успешный статус на UI и файл на диске
    assert "УСПЕШНО ПРИМЕНЕНО" in window.lbl_status.text()
    created_file = os.path.join(root_dir, "gui_file.py")
    assert os.path.exists(created_file)

    # Проверяем появление виджета в истории сессий
    assert window.history_layout.count() == 1
    session_card = window.history_layout.itemAt(0).widget()

    # Ищем кнопку "Откатить" внутри карточки истории
    btn_undo = session_card.findChild(QPushButton)
    assert btn_undo is not None
    assert btn_undo.text() == "Откатить"

    # Мокаем предупреждение отката на "Yes" и кликаем "Откатить"
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.Yes)
    qtbot.mouseClick(btn_undo, Qt.LeftButton)

    # Файл должен удалиться с диска!
    assert os.path.exists(created_file) is False

    # Кнопка в карточке должна поменяться на "Применить снова"
    session_card_updated = window.history_layout.itemAt(0).widget()
    btn_reapply = session_card_updated.findChild(QPushButton)
    assert btn_reapply.text() == "Применить снова"

    # Нажимаем "Применить снова"
    qtbot.mouseClick(btn_reapply, Qt.LeftButton)
    assert os.path.exists(created_file) is True


def test_gui_e2e_context_file_picker_and_viewer(qtbot, gui_window, monkeypatch):
    """E2E: Модальные окна прикрепления файлов контекста и просмотрщика."""
    window, db, root_dir = gui_window
    p_id = db.add_project("Context Project", root_dir)
    window.load_projects()
    window.select_project(window.project_list.item(0))

    # 1. Мокаем выбор файлов в ContextFilePickerModal
    monkeypatch.setattr(ContextFilePickerModal, "exec", lambda self: True)
    monkeypatch.setattr(ContextFilePickerModal, "get_selected_files", lambda self: [("app.py", 0), ("ro.txt", 1)])

    window.open_file_picker()
    assert window.lbl_files_count.text() == "ПРИКРЕПЛЕННЫЕ ФАЙЛЫ (2)"

    # 2. Тестируем модалку просмотра/удаления прикрепленных файлов
    modal_viewer = AttachedFilesViewModal(db.get_project_files(p_id))
    assert modal_viewer.list_widget.count() == 2

    # Меняем статус файла с Read-Only на Writable
    modal_viewer.toggle_status("ro.txt")
    assert modal_viewer.file_states["ro.txt"] == 0

    # Удаляем один файл из списка
    modal_viewer.remove_file("app.py")
    assert len(modal_viewer.get_files()) == 1


def test_gui_e2e_dump_and_clear_history(qtbot, gui_window, monkeypatch):
    """E2E: Создание дампа и очистка истории сессий через GUI."""
    window, db, root_dir = gui_window
    p_id = db.add_project("Dump Project", root_dir)
    window.load_projects()
    window.select_project(window.project_list.item(0))

    # Выполняем одну сессию
    window.code_editor.setPlainText('<fs_create path="demo.txt">hello</fs_create>')
    window.run_execution()
    assert window.history_layout.count() == 1

    # 1. Нажимаем "СОЗДАТЬ ДАМП КОНТЕКСТА" (мокаем QMessageBox.information)
    monkeypatch.setattr(QMessageBox, "information", lambda *args: None)
    window.make_dump()
    assert os.path.exists(os.path.join(root_dir, "context_dump.txt"))

    # 2. Нажимаем "Очистить историю сессий"
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.Yes)
    window.clear_history()

    # Проверяем, что история на виджете опустела
    assert window.history_layout.count() == 0
    assert len(db.get_executions(p_id)) == 0