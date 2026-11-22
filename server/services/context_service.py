import os
from typing import Any, Dict, List
from server.services.ignore_service import IgnoreService


class ContextService:
    def __init__(self, ignore_service: IgnoreService) -> None:
        self.ignore = ignore_service

    @staticmethod
    def is_binary_file(filepath: str, sample_size: int = 8192) -> bool:
        try:
            with open(filepath, "rb") as f:
                chunk = f.read(sample_size)
                if b"\x00" in chunk:
                    return True
            return False
        except Exception:
            return True

    @staticmethod
    def is_test_file(filename: str) -> bool:
        base = os.path.basename(filename).lower()
        stem, _ = os.path.splitext(base)
        return (
            stem.startswith("test_")
            or stem.endswith("_test")
            or "_test." in base
            or ".test." in base
            or ".spec." in base
            or stem.endswith(".test")
            or stem.endswith(".spec")
        )

    def build_file_tree(self, project_root: str, file_rules: Dict[str, str]) -> List[Dict[str, Any]]:
        rules = self.ignore.get_project_rules(project_root)
        tree = []

        for root, dirs, files in os.walk(project_root):
            rel_dir = os.path.relpath(root, project_root).replace("\\", "/")
            if rel_dir == ".":
                rel_dir = ""

            dirs[:] = [
                d for d in dirs
                if not self.ignore.is_ignored(
                    f"{rel_dir}/{d}" if rel_dir else d, is_dir=True, rules=rules
                )
            ]

            for file in sorted(files):
                rel_file = f"{rel_dir}/{file}" if rel_dir else file
                if rel_file == "context_dump.txt" and rel_file not in file_rules:
                    continue
                if self.ignore.is_ignored(rel_file, is_dir=False, rules=rules):
                    continue

                state = file_rules.get(rel_file, "unmarked")
                tree.append({
                    "path": rel_file,
                    "name": file,
                    "state": state
                })

        return tree

    def generate_dump(
        self,
        project_root: str,
        file_rules: Dict[str, str],
        include_unmarked_names: bool = False,
        ignore_tests: bool = False
    ) -> str:
        rules = self.ignore.get_project_rules(project_root)
        dump_sections = []
        unmarked_paths = []

        dump_sections.append("=" * 60)
        dump_sections.append("PROJECT CONTEXT DUMP")
        dump_sections.append("=" * 60 + "\n")

        for root, dirs, files in os.walk(project_root):
            rel_dir = os.path.relpath(root, project_root).replace("\\", "/")
            if rel_dir == ".":
                rel_dir = ""

            dirs[:] = [
                d for d in dirs
                if not self.ignore.is_ignored(
                    f"{rel_dir}/{d}" if rel_dir else d, is_dir=True, rules=rules
                )
            ]

            for file in sorted(files):
                rel_file = f"{rel_dir}/{file}" if rel_dir else file
                if rel_file == "context_dump.txt" and rel_file not in file_rules:
                    continue
                if self.ignore.is_ignored(rel_file, is_dir=False, rules=rules):
                    continue

                state = file_rules.get(rel_file, "unmarked")
                is_test = ignore_tests and self.is_test_file(file)

                if state in ("writable", "readonly"):
                    abs_file = os.path.join(project_root, rel_file)
                    mark = "[WRITABLE]" if state == "writable" else "[READ_ONLY]"

                    dump_sections.append(f"--- START FILE: {rel_file} {mark} ---")

                    if is_test:
                        dump_sections.append("# [TEST FILE EXCLUDED - EXISTS ON DISK]")
                    elif self.is_binary_file(abs_file):
                        dump_sections.append("# [BINARY FILE EXCLUDED]")
                    else:
                        try:
                            with open(abs_file, "r", encoding="utf-8", errors="replace", newline="") as f:
                                dump_sections.append(f.read())
                        except Exception as e:
                            dump_sections.append(f"# [ERROR READING FILE: {str(e)}]")

                    dump_sections.append(f"--- END FILE: {rel_file} ---\n")

                elif state == "unmarked" and include_unmarked_names and not is_test:
                    unmarked_paths.append(rel_file)

        if include_unmarked_names and unmarked_paths:
            dump_sections.append("\n" + "=" * 60)
            dump_sections.append("=== UNMARKED PROJECT STRUCTURE (NAMES ONLY) ===")
            dump_sections.append("=" * 60)
            for p in sorted(unmarked_paths):
                dump_sections.append(f"[UNMARKED]: {p}")
            dump_sections.append("=" * 60 + "\n")

        return "\n".join(dump_sections)