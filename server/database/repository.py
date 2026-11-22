import json
import os
import sqlite3
from contextlib import contextmanager
from typing import Dict, List, Optional
from server.database.models import (
    ChangeRecordModel,
    ExecutionSessionModel,
    ProfileFileRuleModel,
    ProfileModel,
    ProjectModel,
)


class DatabaseRepository:
    def __init__(self, db_path: str = "fs_orchestrator.db") -> None:
        self.db_path = db_path
        self._init_tables()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA busy_timeout = 15000;")
        try:
            yield conn
        finally:
            conn.close()

    def _init_tables(self) -> None:
        with self._get_connection() as conn:
            conn.execute("PRAGMA journal_mode = WAL;")
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                root_dir TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                is_default INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                UNIQUE(project_id, name)
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS profile_file_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL,
                rel_path TEXT NOT NULL,
                state TEXT NOT NULL,
                FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE,
                UNIQUE(profile_id, rel_path)
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS execution_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                profile_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL,
                total_commands INTEGER NOT NULL,
                error_count INTEGER NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS change_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                command_tag TEXT NOT NULL,
                target_path TEXT,
                status TEXT NOT NULL,
                error_details TEXT,
                original_snapshot TEXT,
                new_snapshot TEXT,
                FOREIGN KEY (session_id) REFERENCES execution_sessions(id) ON DELETE CASCADE
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                profile_id INTEGER,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                snapshot_data TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """)
            conn.commit()

    def create_project(self, name: str, root_dir: str) -> ProjectModel:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO projects (name, root_dir, created_at) VALUES (?, ?, datetime('now'))",
                (name, root_dir)
            )
            project_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO profiles (project_id, name, is_default) VALUES (?, 'default', 1)",
                (project_id,)
            )
            conn.commit()
            return ProjectModel(id=project_id, name=name, root_dir=root_dir)

    def list_projects(self) -> List[ProjectModel]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            rows = cursor.execute("SELECT id, name, root_dir, created_at FROM projects ORDER BY id DESC").fetchall()
            return [ProjectModel(id=r["id"], name=r["name"], root_dir=r["root_dir"], created_at=r["created_at"]) for r in rows]

    def get_project(self, project_id: int) -> Optional[ProjectModel]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
            if not row:
                return None
            return ProjectModel(id=row["id"], name=row["name"], root_dir=row["root_dir"], created_at=row["created_at"])

    def delete_project(self, project_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            conn.commit()
            return cursor.rowcount > 0

    def list_profiles(self, project_id: int) -> List[ProfileModel]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT id, project_id, name, is_default FROM profiles WHERE project_id = ? ORDER BY is_default DESC, name ASC",
                (project_id,)
            ).fetchall()
            return [ProfileModel(id=r["id"], project_id=r["project_id"], name=r["name"], is_default=bool(r["is_default"])) for r in rows]

    def create_profile(self, project_id: int, name: str) -> ProfileModel:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO profiles (project_id, name, is_default) VALUES (?, ?, 0)",
                (project_id, name)
            )
            profile_id = cursor.lastrowid
            conn.commit()
            return ProfileModel(id=profile_id, project_id=project_id, name=name, is_default=False)

    def delete_profile(self, profile_id: int) -> bool:
        with self._get_connection() as conn:
            row = conn.execute("SELECT project_id FROM profiles WHERE id = ?", (profile_id,)).fetchone()
            if not row:
                return False
            project_id = row["project_id"]
            conn.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
            conn.commit()

            count = conn.execute("SELECT COUNT(*) as c FROM profiles WHERE project_id = ?", (project_id,)).fetchone()["c"]
            if count == 0:
                conn.execute("INSERT INTO profiles (project_id, name, is_default) VALUES (?, 'default', 1)", (project_id,))
                conn.commit()

            return True

    def get_profile_rules(self, profile_id: int) -> Dict[str, str]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT rel_path, state FROM profile_file_rules WHERE profile_id = ?",
                (profile_id,)
            ).fetchall()
            return {r["rel_path"]: r["state"] for r in rows}

    def set_profile_file_rule(self, profile_id: int, rel_path: str, state: str) -> None:
        with self._get_connection() as conn:
            if state == "unmarked":
                conn.execute(
                    "DELETE FROM profile_file_rules WHERE profile_id = ? AND rel_path = ?",
                    (profile_id, rel_path)
                )
            else:
                conn.execute(
                    """
                    INSERT INTO profile_file_rules (profile_id, rel_path, state)
                    VALUES (?, ?, ?)
                    ON CONFLICT(profile_id, rel_path) DO UPDATE SET state = excluded.state
                    """,
                    (profile_id, rel_path, state)
                )
            conn.commit()

    def set_profile_file_rules_bulk(self, profile_id: int, rules: List[tuple]) -> None:
        with self._get_connection() as conn:
            for rel_path, state in rules:
                if state == "unmarked":
                    conn.execute(
                        "DELETE FROM profile_file_rules WHERE profile_id = ? AND rel_path = ?",
                        (profile_id, rel_path)
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO profile_file_rules (profile_id, rel_path, state)
                        VALUES (?, ?, ?)
                        ON CONFLICT(profile_id, rel_path) DO UPDATE SET state = excluded.state
                        """,
                        (profile_id, rel_path, state)
                    )
            conn.commit()

    def clear_profile_rules(self, profile_id: int) -> None:
        with self._get_connection() as conn:
            conn.execute(
                "DELETE FROM profile_file_rules WHERE profile_id = ?",
                (profile_id,)
            )
            conn.commit()

    def record_session(
        self,
        project_id: int,
        profile_id: int,
        status: str,
        total_commands: int,
        error_count: int,
        records: List[ChangeRecordModel]
    ) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO execution_sessions (project_id, profile_id, created_at, status, total_commands, error_count)
                VALUES (?, ?, datetime('now'), ?, ?, ?)
                """,
                (project_id, profile_id, status, total_commands, error_count)
            )
            session_id = cursor.lastrowid

            for rec in records:
                cursor.execute(
                    """
                    INSERT INTO change_records (session_id, command_tag, target_path, status, error_details, original_snapshot, new_snapshot)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (session_id, rec.command_tag, rec.target_path, rec.status, rec.error_details, rec.original_snapshot, rec.new_snapshot)
                )

            conn.commit()
            return session_id

    def list_sessions(self, project_id: int, limit: int = 50) -> List[dict]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT s.id, s.created_at, s.status, s.total_commands, s.error_count, p.name as profile_name
                FROM execution_sessions s
                LEFT JOIN profiles p ON s.profile_id = p.id
                WHERE s.project_id = ?
                ORDER BY s.id DESC LIMIT ?
                """,
                (project_id, limit)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_session_details(self, session_id: int) -> List[dict]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM change_records WHERE session_id = ? ORDER BY id ASC",
                (session_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def clear_project_history(self, project_id: int) -> None:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM execution_sessions WHERE project_id = ?", (project_id,))
            conn.commit()
        try:
            with self._get_connection() as conn:
                conn.isolation_level = None
                conn.execute("VACUUM;")
        except sqlite3.OperationalError:
            pass

    def create_snapshot(self, project_id: int, profile_id: Optional[int], name: str, data_json: str) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO project_snapshots (project_id, profile_id, name, created_at, snapshot_data)
                VALUES (?, ?, ?, datetime('now'), ?)
                """,
                (project_id, profile_id, name, data_json)
            )
            conn.commit()
            return cursor.lastrowid

    def list_snapshots(self, project_id: int) -> List[dict]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT s.id, s.project_id, s.profile_id, s.name, s.created_at, p.name as profile_name
                FROM project_snapshots s
                LEFT JOIN profiles p ON s.profile_id = p.id
                WHERE s.project_id = ?
                ORDER BY s.id DESC
                """,
                (project_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_snapshot(self, snapshot_id: int) -> Optional[dict]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM project_snapshots WHERE id = ?", (snapshot_id,)).fetchone()
            return dict(row) if row else None

    def delete_snapshot(self, snapshot_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM project_snapshots WHERE id = ?", (snapshot_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO app_settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value)
            )
            conn.commit()