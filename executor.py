import os
import shutil


class CodeExecutor:
    def __init__(self, db):
        self.db = db

    def execute_session(self, project_id, root_dir, instructions, log_callback=None):
        exec_id = self.db.create_execution(project_id)
        project_files = {rel: is_ro for rel, is_ro in self.db.get_project_files(project_id)}

        overall_success = True

        abs_root = os.path.abspath(root_dir)

        for item in instructions:
            rel_path = item['path']
            abs_path = os.path.normpath(os.path.join(abs_root, rel_path))

            # Защита от Path Traversal: не даем выйти за пределы корневой директории проекта через ../
            if not abs_path.startswith(abs_root + os.sep) and abs_path != abs_root:
                err = f"Ошибка: Запрещено. Попытка выхода за пределы папки проекта ({rel_path})."
                if log_callback: log_callback(err)
                self.db.add_change(exec_id, rel_path, item['type'], item.get('search', ''), item.get('replace', ''),
                                   None, 'Error', err)
                overall_success = False
                continue

            # Проверка прав: существующие файлы можно менять ТОЛЬКО если они явно отмечены как Writable (0)
            if os.path.exists(abs_path):
                if project_files.get(rel_path) != 0:
                    err = f"Ошибка: Запись запрещена. Файл {rel_path} не отмечен как [WRITABLE] в проекте."
                    if log_callback: log_callback(err)
                    self.db.add_change(exec_id, rel_path, item['type'], item.get('search', ''), item.get('replace', ''),
                                       None, 'Error', err)
                    overall_success = False
                    continue

            if item['type'] == 'create':
                if os.path.exists(abs_path):
                    err = f"Ошибка: Нельзя создать {rel_path}, файл уже существует."
                    if log_callback: log_callback(err)
                    self.db.add_change(exec_id, rel_path, 'create', '', item['content'], None, 'Error', err)
                    overall_success = False
                else:
                    try:
                        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                        with open(abs_path, 'w', encoding='utf-8') as f:
                            f.write(item['content'])
                        self.db.add_change(exec_id, rel_path, 'create', '', item['content'], None, 'Success')

                        # Автоматически прописываем новый файл в базу проекта как Writable
                        project_files[rel_path] = 0
                        current_list = self.db.get_project_files(project_id)
                        current_list.append((rel_path, 0))
                        self.db.set_project_files(project_id, current_list)

                        if log_callback: log_callback(f"Создан файл: {rel_path}")
                    except Exception as e:
                        err = f"Ошибка создания {rel_path}: {str(e)}"
                        if log_callback: log_callback(err)
                        self.db.add_change(exec_id, rel_path, 'create', '', item['content'], None, 'Error', err)
                        overall_success = False

            elif item['type'] == 'edit':
                if not os.path.exists(abs_path):
                    err = f"Ошибка: Файл {rel_path} не найден для изменения."
                    if log_callback: log_callback(err)
                    self.db.add_change(exec_id, rel_path, 'edit', item['search'], item['replace'], None, 'Error', err)
                    overall_success = False
                    continue

                try:
                    with open(abs_path, 'r', encoding='utf-8') as f:
                        original_content = f.read()

                    new_content = None
                    if item['replace_all']:
                        new_content = item['replace']
                    else:
                        # Поиск с допуском пробелов
                        if item['search'] in original_content:
                            new_content = original_content.replace(item['search'], item['replace'])
                        else:
                            # Пробуем без лишних концевых пробелов
                            s_clean = "\n".join([line.rstrip() for line in item['search'].splitlines()])
                            o_clean_lines = [line.rstrip() for line in original_content.splitlines()]
                            o_clean_text = "\n".join(o_clean_lines)

                            if s_clean in o_clean_text:
                                new_content = o_clean_text.replace(s_clean, item['replace'])

                    if new_content is not None:
                        with open(abs_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        self.db.add_change(exec_id, rel_path, 'edit', item['search'], item['replace'], original_content,
                                           'Success')
                        if log_callback: log_callback(f"Изменен файл: {rel_path}")
                    else:
                        err = f"Ошибка: Блок поиска не найден в файле {rel_path}"
                        if log_callback: log_callback(err)
                        self.db.add_change(exec_id, rel_path, 'edit', item['search'], item['replace'], original_content,
                                           'Error', err)
                        overall_success = False

                except Exception as e:
                    err = f"Ошибка изменения {rel_path}: {str(e)}"
                    if log_callback: log_callback(err)
                    self.db.add_change(exec_id, rel_path, 'edit', item['search'], item['replace'], None, 'Error', err)
                    overall_success = False

        status_str = "Success" if overall_success else "Error"
        self.db.update_execution_status(exec_id, status_str)
        return overall_success

    # --- Добавить внутрь класса CodeExecutor в executor.py ---
    def is_modified_manually(self, change_id, root_dir):
            cursor = self.db.conn.execute(
                "SELECT file_path, change_type, search_content, replace_content, original_snapshot FROM changes WHERE id=?",
                (change_id,))
            row = cursor.fetchone()
            if not row:
                return False

            file_path, c_type, s_c, r_c, snapshot = row
            abs_path = os.path.normpath(os.path.join(root_dir, file_path))

            if not os.path.exists(abs_path):
                return False

            try:
                with open(abs_path, 'r', encoding='utf-8') as f:
                    current_content = f.read()

                if c_type == 'create':
                    return current_content != r_c
                elif c_type == 'edit':
                    if snapshot is None:
                        return False
                    # Ожидаемое содержимое файла после успешной заправки ИИ
                    if s_c and ('<all />' in s_c or '<all/>' in s_c):
                        expected = r_c
                    else:
                        expected = snapshot.replace(s_c, r_c)

                    return current_content != expected
            except Exception:
                return False

            return False

    def rollback_change(self, change_id, root_dir):
        # Получаем данные изменения из БД напрямую
        cursor = self.db.conn.execute(
            "SELECT file_path, change_type, original_snapshot, status FROM changes WHERE id=?", (change_id,))
        row = cursor.fetchone()
        if not row: return False, "Запись не найдена"

        file_path, c_type, snapshot, status = row
        abs_root = os.path.abspath(root_dir)
        abs_path = os.path.normpath(os.path.join(abs_root, file_path))

        # Защита от выхода за границы директории
        if not abs_path.startswith(abs_root + os.sep) and abs_path != abs_root:
            return False, "Запрещено: попытка выхода за пределы корневой папки проекта"

        try:
            if c_type == 'create':
                if os.path.exists(abs_path):
                    os.remove(abs_path)
            elif c_type == 'edit':
                if snapshot is not None:
                    with open(abs_path, 'w', encoding='utf-8') as f:
                        f.write(snapshot)

            self.db.update_change_status(change_id, 'RolledBack')
            return True, "Откачено успешно"
        except Exception as e:
            return False, str(e)

    def reapply_change(self, change_id, root_dir):
        cursor = self.db.conn.execute(
            "SELECT file_path, change_type, search_content, replace_content FROM changes WHERE id=?", (change_id,))
        row = cursor.fetchone()
        if not row: return False, "Запись не найдена"

        file_path, c_type, s_c, r_c = row
        abs_root = os.path.abspath(root_dir)
        abs_path = os.path.normpath(os.path.join(abs_root, file_path))

        # Защита от выхода за границы директории
        if not abs_path.startswith(abs_root + os.sep) and abs_path != abs_root:
            return False, "Запрещено: попытка выхода за пределы корневой папки проекта"

        try:
            if c_type == 'create':
                os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                with open(abs_path, 'w', encoding='utf-8') as f:
                    f.write(r_c)
            elif c_type == 'edit':
                with open(abs_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                if s_c and ('<all />' in s_c or '<all/>' in s_c):
                    new_content = r_c
                else:
                    new_content = content.replace(s_c, r_c)

                with open(abs_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)

            self.db.update_change_status(change_id, 'Success')
            return True, "Применено повторно"
        except Exception as e:
            err_msg = str(e)
            self.db.update_change_status(change_id, 'Error', err_msg)
            return False, err_msg

    def generate_dump(self, project_id, root_dir):
        files = self.db.get_project_files(project_id)
        dump_path = os.path.join(root_dir, "context_dump.txt")

        try:
            with open(dump_path, 'w', encoding='utf-8') as out:
                for rel_path, is_ro in files:
                    abs_path = os.path.normpath(os.path.join(root_dir, rel_path))

                    # 1. Пропускаем пути, которые являются папками, а не файлами
                    if os.path.isdir(abs_path):
                        continue

                    out.write(f"{rel_path}\n")
                    if is_ro == 1:
                        out.write("[READ_ONLY]\n")

                    if os.path.exists(abs_path):
                        try:
                            # 2. Быстрая проверка на бинарный файл (картинка, exe, pyc и т.д.)
                            with open(abs_path, 'rb') as f_bin:
                                chunk = f_bin.read(1024)
                                if b'\x00' in chunk: # Нулевой байт — верный признак бинарника
                                    out.write("# [БИНАРНЫЙ ФАЙЛ ПРОПУЩЕН]\n")
                                    out.write("\n----------\n\n")
                                    continue

                            # 3. Безопасное чтение текста с защитой от сбоев кодировки
                            with open(abs_path, 'r', encoding='utf-8', errors='replace') as f:
                                out.write(f.read())
                        except Exception as read_err:
                            out.write(f"# ОШИБКА ЧТЕНИЯ ФАЙЛА: {str(read_err)}\n")
                    else:
                        out.write("# ФАЙЛ НЕ НАЙДЕН НА ДИСКЕ\n")
                    out.write("\n----------\n\n")
            return True, dump_path
        except Exception as e:
            return False, str(e)