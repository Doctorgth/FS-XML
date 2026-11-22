import os
import tempfile
from server.services.ignore_service import IgnoreService
from server.services.context_service import ContextService


def test_ignore_rules():
    ignore = IgnoreService()
    rules = ["*.log", "node_modules/", "temp_*"]

    assert ignore.is_ignored("app.log", is_dir=False, rules=rules) is True
    assert ignore.is_ignored("node_modules/pkg/index.js", is_dir=False, rules=rules) is True
    assert ignore.is_ignored("node_modules", is_dir=True, rules=rules) is True
    assert ignore.is_ignored("src/index.ts", is_dir=False, rules=rules) is False


def test_binary_detection_and_dump():
    with tempfile.TemporaryDirectory() as temp_dir:
        # Текстовый файл
        txt_file = os.path.join(temp_dir, "test.txt")
        with open(txt_file, "w", encoding="utf-8") as f:
            f.write("Normal Text Content")

        # Бинарный файл с нуль-байтами
        bin_file = os.path.join(temp_dir, "test.bin")
        with open(bin_file, "wb") as f:
            f.write(b"\x00\x01\x02\xFF")

        ignore = IgnoreService()
        ctx = ContextService(ignore)

        assert ctx.is_binary_file(bin_file) is True
        assert ctx.is_binary_file(txt_file) is False

        rules = {"test.txt": "writable", "test.bin": "readonly"}
        dump = ctx.generate_dump(temp_dir, rules, include_unmarked_names=True)

        assert "Normal Text Content" in dump
        assert "[BINARY FILE EXCLUDED]" in dump


def test_ignore_tests_in_dump():
    with tempfile.TemporaryDirectory() as temp_dir:
        app_file = os.path.join(temp_dir, "app.py")
        test_prefix_file = os.path.join(temp_dir, "test_app.py")
        test_suffix_file = os.path.join(temp_dir, "user_test.ts")
        unmarked_test_file = os.path.join(temp_dir, "test_unmarked.py")

        with open(app_file, "w", encoding="utf-8") as f:
            f.write("APP_CODE_BODY")
        with open(test_prefix_file, "w", encoding="utf-8") as f:
            f.write("SECRET_TEST_PREFIX_BODY")
        with open(test_suffix_file, "w", encoding="utf-8") as f:
            f.write("SECRET_TEST_SUFFIX_BODY")
        with open(unmarked_test_file, "w", encoding="utf-8") as f:
            f.write("SECRET_UNMARKED_TEST_BODY")

        ignore = IgnoreService()
        ctx = ContextService(ignore)

        assert ctx.is_test_file("test_app.py") is True
        assert ctx.is_test_file("user_test.ts") is True
        assert ctx.is_test_file("app_test.spec.ts") is True
        assert ctx.is_test_file("app.py") is False
        assert ctx.is_test_file("testing.py") is False

        rules = {
            "app.py": "writable",
            "test_app.py": "writable",
            "user_test.ts": "readonly",
        }

        # С выключенным ignore_tests содержимое тестов попадает в дамп
        dump_with_tests = ctx.generate_dump(temp_dir, rules, include_unmarked_names=True, ignore_tests=False)
        assert "SECRET_TEST_PREFIX_BODY" in dump_with_tests
        assert "SECRET_TEST_SUFFIX_BODY" in dump_with_tests
        assert "test_unmarked.py" in dump_with_tests

        # С включенным ignore_tests=True:
        # - обычный файл с содержимым
        # - отмеченные тестовые файлы помечены как существующие, но без содержимого
        # - неотмеченный тестовый файл не добавляется в дамп даже при include_unmarked_names=True
        dump_without_tests = ctx.generate_dump(temp_dir, rules, include_unmarked_names=True, ignore_tests=True)
        assert "APP_CODE_BODY" in dump_without_tests
        assert "--- START FILE: test_app.py [WRITABLE] ---" in dump_without_tests
        assert "--- START FILE: user_test.ts [READ_ONLY] ---" in dump_without_tests
        assert "[TEST FILE EXCLUDED - EXISTS ON DISK]" in dump_without_tests
        assert "SECRET_TEST_PREFIX_BODY" not in dump_without_tests
        assert "SECRET_TEST_SUFFIX_BODY" not in dump_without_tests
        assert "test_unmarked.py" not in dump_without_tests