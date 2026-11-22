import fnmatch
import os
from typing import List


class IgnoreService:
    def __init__(self, global_ignore_path: str = "fsignore_global") -> None:
        self.global_ignore_path = global_ignore_path
        self.global_rules = self._load_rules_from_file(global_ignore_path)

    def reload_global_rules(self) -> None:
        self.global_rules = self._load_rules_from_file(self.global_ignore_path)

    @staticmethod
    def _load_rules_from_file(path: str) -> List[str]:
        if not os.path.isfile(path):
            return []
        rules = []
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue

                # Обработка inline-комментариев (например: "file.txt # мой коммент"),
                # но сохраняем экранированный "\#"
                if "#" in line:
                    idx = 0
                    clean_chars = []
                    while idx < len(line):
                        if line[idx] == "\\" and idx + 1 < len(line) and line[idx + 1] == "#":
                            clean_chars.append("#")
                            idx += 2
                            continue
                        if line[idx] == "#":
                            break
                        clean_chars.append(line[idx])
                        idx += 1
                    line = "".join(clean_chars).strip()

                if not line:
                    continue

                clean_rule = line.replace("\\", "/")
                rules.append(clean_rule)
        return rules

    def get_project_rules(self, project_root: str) -> List[str]:
        self.reload_global_rules()
        project_ignore_file = os.path.join(project_root, ".fsignore")
        local_rules = self._load_rules_from_file(project_ignore_file)
        return self.global_rules + local_rules

    @staticmethod
    def is_ignored(rel_path: str, is_dir: bool, rules: List[str]) -> bool:
        clean_path = rel_path.strip().replace("\\", "/").strip("/")
        if not clean_path:
            return False

        path_parts = clean_path.split("/")
        file_or_dir_name = path_parts[-1]
        ancestor_dirs = ["/".join(path_parts[:i]) for i in range(1, len(path_parts))]

        for rule in rules:
            anchored = rule.startswith("/")
            dir_only = rule.endswith("/")
            r = rule.strip("/")
            if not r:
                continue

            # Правило для директорий: проверяем только саму директорию или родительские директории
            if dir_only:
                if anchored:
                    if is_dir and fnmatch.fnmatch(clean_path, r):
                        return True
                    if any(fnmatch.fnmatch(anc, r) for anc in ancestor_dirs):
                        return True
                elif "/" in r:
                    candidates = ancestor_dirs + ([clean_path] if is_dir else [])
                    for cand in candidates:
                        if cand == r or cand.endswith("/" + r) or fnmatch.fnmatch(cand, r):
                            return True
                else:
                    if is_dir and fnmatch.fnmatch(file_or_dir_name, r):
                        return True
                    if any(fnmatch.fnmatch(part, r) for part in path_parts[:-1]):
                        return True
                continue

            # Правило с ведущим '/' (привязано к корню проекта)
            if anchored:
                if fnmatch.fnmatch(clean_path, r):
                    return True
                if any(fnmatch.fnmatch(anc, r) for anc in ancestor_dirs):
                    return True
                continue

            # Составное правило (например 'src/*.ts' или 'foo/bar')
            if "/" in r:
                if fnmatch.fnmatch(clean_path, r):
                    return True
                if any(fnmatch.fnmatch(anc, r) or anc.endswith("/" + r) for anc in ancestor_dirs):
                    return True
                continue

            # Совпадение по имени папки/файла (например 'test' матчит 'test', но НЕ 'text.txt')
            if fnmatch.fnmatch(file_or_dir_name, r):
                return True

            if any(fnmatch.fnmatch(part, r) for part in path_parts[:-1]):
                return True

        return False