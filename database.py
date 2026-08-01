import sqlite3
import json
from datetime import datetime

class Database:
    def __init__(self, db_path="app_data.db"):
        self.conn = sqlite3.connect(db_path)
        self.create_tables()

    def create_tables(self):
        with self.conn:
            # Проекты
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    root_dir TEXT NOT NULL
                )
            """)
            # Прикрепленные файлы проекта
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS project_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    rel_path TEXT NOT NULL,
                    is_readonly INTEGER DEFAULT 0,
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            """)
            # Сессии выполнения XML
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    timestamp TEXT NOT NULL,
                    status TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            """)
            # Отдельные правки внутри сессии (для отката)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS changes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id INTEGER,
                    file_path TEXT NOT NULL,
                    change_type TEXT NOT NULL, -- 'create' или 'edit'
                    search_content TEXT,
                    replace_content TEXT,
                    original_snapshot TEXT, -- Содержимое ДО замен (None если файл создавался)
                    status TEXT NOT NULL, -- 'Success', 'Error', 'RolledBack'
                    error_msg TEXT,
                    FOREIGN KEY(execution_id) REFERENCES executions(id) ON DELETE CASCADE
                )
            """)

    # --- Управление проектами ---
    def add_project(self, name, root_dir):
        with self.conn:
            cursor = self.conn.execute("INSERT INTO projects (name, root_dir) VALUES (?, ?)", (name, root_dir))
            return cursor.lastrowid

    def get_projects(self):
        cursor = self.conn.execute("SELECT id, name, root_dir FROM projects")
        return cursor.fetchall()

    def update_project(self, project_id, name=None, root_dir=None):
        with self.conn:
            if name:
                self.conn.execute("UPDATE projects SET name=? WHERE id=?", (name, project_id))
            if root_dir:
                self.conn.execute("UPDATE projects SET root_dir=? WHERE id=?", (root_dir, project_id))

    def delete_project(self, project_id):
        with self.conn:
            self.conn.execute("DELETE FROM projects WHERE id=?", (project_id,))

    # --- Файлы контекста ---
    def set_project_files(self, project_id, file_list):
        # file_list: list of tuples (rel_path, is_readonly)
        with self.conn:
            self.conn.execute("DELETE FROM project_files WHERE project_id=?", (project_id,))
            for rel_path, is_ro in file_list:
                self.conn.execute(
                    "INSERT INTO project_files (project_id, rel_path, is_readonly) VALUES (?, ?, ?)",
                    (project_id, rel_path, 1 if is_ro else 0)
                )

    def get_project_files(self, project_id):
        cursor = self.conn.execute("SELECT rel_path, is_readonly FROM project_files WHERE project_id=?", (project_id,))
        return cursor.fetchall()

    # --- История и Откаты ---
    def create_execution(self, project_id):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.conn:
            cursor = self.conn.execute("INSERT INTO executions (project_id, timestamp, status) VALUES (?, ?, ?)",
                                       (project_id, now, "In Progress"))
            return cursor.lastrowid

    def update_execution_status(self, exec_id, status):
        with self.conn:
            self.conn.execute("UPDATE executions SET status=? WHERE id=?", (status, exec_id))

    def add_change(self, exec_id, file_path, change_type, search_c, replace_c, snapshot, status, error_msg=""):
        with self.conn:
            cursor = self.conn.execute("""
                INSERT INTO changes (execution_id, file_path, change_type, search_content, replace_content, original_snapshot, status, error_msg)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (exec_id, file_path, change_type, search_c, replace_c, snapshot, status, error_msg))
            return cursor.lastrowid

    def update_change_status(self, change_id, status, error_msg=""):
        with self.conn:
            self.conn.execute("UPDATE changes SET status=?, error_msg=? WHERE id=?", (status, error_msg, change_id))

    def get_executions(self, project_id):
        cursor = self.conn.execute("SELECT id, timestamp, status FROM executions WHERE project_id=? ORDER BY id DESC", (project_id,))
        execs = cursor.fetchall()
        result = []
        for ex in execs:
            ex_id, ts, st = ex
            c_cursor = self.conn.execute(
                "SELECT id, file_path, change_type, search_content, replace_content, original_snapshot, status, error_msg FROM changes WHERE execution_id=?",
                (ex_id,)
            )
            changes = c_cursor.fetchall()
            result.append({'id': ex_id, 'timestamp': ts, 'status': st, 'changes': changes})
        return result


    def clear_project_history(self, project_id):
        # 1. Сначала удаляем записи в транзакции
        with self.conn:
            self.conn.execute("DELETE FROM executions WHERE project_id=?", (project_id,))
        # 2. Вызываем VACUUM строго ВНЕ транзакции
        self.conn.execute("VACUUM")