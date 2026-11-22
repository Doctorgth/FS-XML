import re
from typing import List, Optional, Tuple
from core.registry import CommandRegistry, registry as default_registry
from core.sandbox import AccessDeniedException, SecurityException
from core.types import (
    CommandResult,
    CommandType,
    ExecutionBatchResult,
    ExecutionContext,
    ParsedCommandNode,
)


class CoreEngine:
    def __init__(self, cmd_registry: CommandRegistry = default_registry) -> None:
        self.registry = cmd_registry

    def parse_payload(self, raw_text: str) -> List[ParsedCommandNode]:
        nodes: List[ParsedCommandNode] = []
        open_tag_re = re.compile(
            r'<([a-zA-Z0-9_\-]+)((?:\s+(?:"[^"]*"|\'[^\']*\'|[^>"\'/])*)?)\s*(\/?)>',
            re.MULTILINE
        )

        idx = 0
        text_len = len(raw_text)

        while idx < text_len:
            match = open_tag_re.search(raw_text, idx)
            if not match:
                break

            tag_name = match.group(1).lower()
            raw_attrs = match.group(2) or ""
            is_self_closing = match.group(3) == "/"
            start_pos = match.start()
            end_tag_pos = match.end()

            handler = self.registry.get_handler(tag_name)
            if not handler:
                idx = end_tag_pos
                continue

            attributes = self._parse_attributes(raw_attrs)

            if is_self_closing:
                node = ParsedCommandNode(
                    tag=tag_name,
                    attributes=attributes,
                    inner_text="",
                    sub_elements={},
                    raw_snippet=raw_text[start_pos:end_tag_pos]
                )
                nodes.append(node)
                idx = end_tag_pos
                continue

            # Если тег команды упомянут в тексте без атрибута path (например: "Ниже <fs_edit>:"),
            # а до закрывающего тега встречается реальная команда с path=..., пропускаем упоминание.
            if tag_name in ("fs_edit", "fs_create") and "path" not in attributes:
                next_close = re.search(rf"</{re.escape(tag_name)}\s*>", raw_text[end_tag_pos:], re.IGNORECASE)
                if next_close:
                    between = raw_text[end_tag_pos : end_tag_pos + next_close.start()]
                    if re.search(rf"<{re.escape(tag_name)}\s+[^>]*\bpath\s*=", between, re.IGNORECASE):
                        idx = end_tag_pos
                        continue

            if tag_name == "fs_edit":
                parsed_edit = self._parse_fs_edit_block(raw_text, end_tag_pos)
                if parsed_edit is not None:
                    close_start, close_end, pairs = parsed_edit
                    content = raw_text[end_tag_pos:close_start]
                    sub_elements = {}
                    if pairs:
                        sub_elements["fs_search"] = pairs[0][0]
                        sub_elements["fs_replace"] = pairs[0][1]
                    full_snippet = raw_text[start_pos:close_end]
                    nodes.append(
                        ParsedCommandNode(
                            tag=tag_name,
                            attributes=attributes,
                            inner_text=content,
                            sub_elements=sub_elements,
                            edit_pairs=pairs,
                            raw_snippet=full_snippet
                        )
                    )
                    idx = close_end
                    continue

            close_bounds = self._find_matching_close(raw_text, end_tag_pos, tag_name)
            if close_bounds is None:
                idx = end_tag_pos
                continue

            close_idx, close_end = close_bounds
            content = raw_text[end_tag_pos:close_idx]
            sub_elements = self._extract_sub_elements(content)

            full_snippet = raw_text[start_pos:close_end]
            nodes.append(
                ParsedCommandNode(
                    tag=tag_name,
                    attributes=attributes,
                    inner_text=content,
                    sub_elements=sub_elements,
                    raw_snippet=full_snippet
                )
            )
            idx = close_end

        return nodes

    @staticmethod
    def _is_quoted_literal_tag(raw_text: str, start: int, end: int) -> bool:
        if start > 0 and end < len(raw_text):
            prev_ch = raw_text[start - 1]
            next_ch = raw_text[end]
            if prev_ch in ('"', "'") and next_ch == prev_ch:
                return True
        return False

    def _find_matching_close(
        self, raw_text: str, start_idx: int, tag_name: str
    ) -> Optional[Tuple[int, int]]:
        tag_re = re.compile(
            rf'<(/?){re.escape(tag_name)}((?:\s+(?:"[^"]*"|\'[^\']*\'|[^>"\'/])*)?)\s*(\/?)>',
            re.IGNORECASE | re.MULTILINE,
        )
        depth = 1
        pos = start_idx
        text_len = len(raw_text)

        while pos < text_len:
            m = tag_re.search(raw_text, pos)
            if not m:
                break

            if self._is_quoted_literal_tag(raw_text, m.start(), m.end()):
                pos = m.end()
                continue

            is_closing = m.group(1) == "/"
            is_self_closing = m.group(3) == "/"

            if is_closing:
                if depth > 1:
                    depth -= 1
                else:
                    return m.start(), m.end()
            elif not is_self_closing:
                depth += 1

            pos = m.end()

        # Запасной проход без учёта глубины на случай непарного открывающего тега внутри строкового литерала кода
        close_only_re = re.compile(rf"</{re.escape(tag_name)}\s*>", re.IGNORECASE)
        pos = start_idx
        while pos < text_len:
            m = close_only_re.search(raw_text, pos)
            if not m:
                return None
            if self._is_quoted_literal_tag(raw_text, m.start(), m.end()):
                pos = m.end()
                continue
            return m.start(), m.end()
        return None

    def _parse_fs_edit_block(
        self, raw_text: str, start_idx: int
    ) -> Optional[Tuple[int, int, List[Tuple[str, str]]]]:
        res = self._scan_fs_edit_pairs(raw_text, start_idx, track_nesting=True)
        if res is not None:
            return res
        return self._scan_fs_edit_pairs(raw_text, start_idx, track_nesting=False)

    def _scan_fs_edit_pairs(
        self, raw_text: str, start_idx: int, track_nesting: bool
    ) -> Optional[Tuple[int, int, List[Tuple[str, str]]]]:
        ws_or_comment = r"(?:\s|<!--.*?-->)*"
        open_search_re = re.compile(rf"{ws_or_comment}<\s*fs_search(?:\s+[^>]*)?>", re.IGNORECASE | re.DOTALL)
        open_replace_re = re.compile(rf"{ws_or_comment}<\s*fs_replace(?:\s+[^>]*)?>", re.IGNORECASE | re.DOTALL)
        close_edit_re = re.compile(rf"{ws_or_comment}</\s*fs_edit\s*>", re.IGNORECASE | re.DOTALL)

        search_tag_re = re.compile(r"<(/?)fs_search(?:\s+[^>]*)?\s*(/?)>", re.IGNORECASE)
        replace_tag_re = re.compile(r"<(/?)fs_replace(?:\s+[^>]*)?\s*(/?)>", re.IGNORECASE)

        pairs: List[Tuple[str, str]] = []
        pos = start_idx
        text_len = len(raw_text)

        while pos < text_len:
            m_open_search = open_search_re.match(raw_text, pos)
            if not m_open_search:
                return None

            search_content_start = m_open_search.end()
            search_depth = 1
            s_pos = search_content_start
            search_end = -1
            replace_open_match = None

            while s_pos < text_len:
                ms = search_tag_re.search(raw_text, s_pos)
                if not ms:
                    return None
                if self._is_quoted_literal_tag(raw_text, ms.start(), ms.end()):
                    s_pos = ms.end()
                    continue
                is_closing = ms.group(1) == "/"
                is_self_closing = ms.group(2) == "/"

                if is_closing:
                    if track_nesting and search_depth > 1:
                        search_depth -= 1
                    else:
                        mr = open_replace_re.match(raw_text, ms.end())
                        if mr:
                            search_end = ms.start()
                            replace_open_match = mr
                            break
                elif track_nesting and not is_self_closing:
                    search_depth += 1

                s_pos = ms.end()

            if search_end == -1 or replace_open_match is None:
                return None

            search_text = raw_text[search_content_start:search_end]
            replace_content_start = replace_open_match.end()
            replace_depth = 1
            r_pos = replace_content_start

            while r_pos < text_len:
                mr = replace_tag_re.search(raw_text, r_pos)
                if not mr:
                    return None
                if self._is_quoted_literal_tag(raw_text, mr.start(), mr.end()):
                    r_pos = mr.end()
                    continue
                is_closing = mr.group(1) == "/"
                is_self_closing = mr.group(2) == "/"

                if is_closing:
                    if track_nesting and replace_depth > 1:
                        replace_depth -= 1
                    else:
                        me = close_edit_re.match(raw_text, mr.end())
                        if me:
                            after_edit = raw_text[me.end():]
                            if not re.match(r'[ \t]*["\']', after_edit):
                                replace_text = raw_text[replace_content_start:mr.start()]
                                pairs.append((search_text, replace_text))
                                close_tag_m = re.search(r"</\s*fs_edit\s*>$", me.group(0), re.IGNORECASE)
                                edit_close_start = me.start() + (close_tag_m.start() if close_tag_m else 0)
                                return edit_close_start, me.end(), pairs

                        next_s = open_search_re.match(raw_text, mr.end())
                        if next_s:
                            replace_text = raw_text[replace_content_start:mr.start()]
                            pairs.append((search_text, replace_text))
                            pos = mr.end()
                            break
                elif track_nesting and not is_self_closing:
                    replace_depth += 1

                r_pos = mr.end()
            else:
                return None

        return None

    def _parse_attributes(self, attrs_str: str) -> dict:
        attrs = {}
        pattern = re.compile(r'([a-zA-Z0-9_\-]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\')')
        for m in pattern.finditer(attrs_str):
            attrs[m.group(1)] = m.group(2) if m.group(2) is not None else m.group(3)
        return attrs

    def _extract_sub_elements(self, content: str) -> dict:
        subs = {}
        sub_re = re.compile(
            r"<([a-zA-Z0-9_\-]+)[^>]*>(.*?)</\1>",
            re.DOTALL
        )
        for m in sub_re.finditer(content):
            subs[m.group(1).lower()] = m.group(2)
        return subs

    def execute_batch(self, raw_input: str, context: ExecutionContext) -> ExecutionBatchResult:
        nodes = self.parse_payload(raw_input)
        batch_res = ExecutionBatchResult(
            total_commands=len(nodes),
            success_count=0,
            error_count=0,
            results=[]
        )

        for node in nodes:
            handler = self.registry.get_handler(node.tag)
            if not handler:
                batch_res.error_count += 1
                batch_res.results.append(
                    CommandResult(
                        tag=node.tag,
                        success=False,
                        message=f"No handler registered for command tag '{node.tag}'"
                    )
                )
                continue

            metadata = handler.metadata

            if metadata.command_type == CommandType.MANAGEMENT and not context.allow_management:
                batch_res.error_count += 1
                batch_res.results.append(
                    CommandResult(
                        tag=node.tag,
                        success=False,
                        target_path=node.attributes.get("path"),
                        message=(
                            f"Security Violation: Command '{node.tag}' is a MANAGEMENT command. "
                            f"Flag 'allow_management' is currently disabled."
                        )
                    )
                )
                continue

            try:
                res = handler.execute(node, context)
            except (SecurityException, AccessDeniedException) as sec_err:
                res = CommandResult(
                    tag=node.tag,
                    success=False,
                    target_path=node.attributes.get("path"),
                    message=f"Security / Access Restriction: {str(sec_err)}"
                )
            except Exception as err:
                res = CommandResult(
                    tag=node.tag,
                    success=False,
                    target_path=node.attributes.get("path"),
                    message=f"Execution Failed with unexpected error: {str(err)}"
                )

            if res.success:
                batch_res.success_count += 1
            else:
                batch_res.error_count += 1

            batch_res.results.append(res)

        return batch_res