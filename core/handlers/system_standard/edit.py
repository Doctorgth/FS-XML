import os
import re
from core.handlers.base import BaseCommandHandler
from core.sandbox import AccessDeniedException, Sandbox, SecurityException
from core.types import (
    CommandMetadata,
    CommandResult,
    CommandType,
    ExecutionContext,
    ParsedCommandNode,
)


def _strip_xml_tag_newlines(text: str) -> str:
    if text.startswith("\r\n"):
        text = text[2:]
    elif text.startswith("\n"):
        text = text[1:]

    if text.endswith("\r\n"):
        text = text[:-2]
    elif text.endswith("\n"):
        text = text[:-1]

    return text


class FsEditHandler(BaseCommandHandler):
    @property
    def metadata(self) -> CommandMetadata:
        tag_name = "fs" + "_" + "edit"
        search_tag = "fs" + "_" + "search"
        replace_tag = "fs" + "_" + "replace"
        return CommandMetadata(
            tag=tag_name,
            command_type=CommandType.STANDARD,
            description_human=(
                f"Редактирование существующего файла: точечная замена (<{search_tag}>/<{replace_tag}>) "
                f"или полная перезапись (<all />)."
            ),
            example_usage=(
                f"<{tag_name} path=\"path/to/file.ext\">\n"
                f"<{search_tag}>\nold\n</{search_tag}>\n"
                f"<{replace_tag}>\nnew\n</{replace_tag}>\n"
                f"</{tag_name}>"
            )
        )

    def execute(self, node: ParsedCommandNode, context: ExecutionContext) -> CommandResult:
        rel_path = node.attributes.get("path")
        if not rel_path:
            return CommandResult(
                tag=self.metadata.tag,
                success=False,
                message="Missing required attribute: 'path'"
            )

        try:
            abs_path = Sandbox.resolve_safe_path(context.root_dir, rel_path)
            norm_rel = Sandbox.normalize_rel_path(rel_path)

            Sandbox.assert_write_permitted(norm_rel, context, check_registered=True)

            if not os.path.isfile(abs_path):
                return CommandResult(
                    tag=self.metadata.tag,
                    success=False,
                    target_path=norm_rel,
                    message=f"Target file '{norm_rel}' does not exist on disk."
                )

            with open(abs_path, "r", encoding="utf-8", errors="replace", newline="") as f:
                original_content = f.read()

            search_key = "fs" + "_" + "search"
            replace_key = "fs" + "_" + "replace"
            all_tag_re = re.compile(r"<\s*all\s*/\s*>", re.IGNORECASE)

            if node.edit_pairs:
                pairs = list(node.edit_pairs)
            else:
                search_block = node.sub_elements.get(search_key)
                replace_block = node.sub_elements.get(replace_key)
                if search_block is not None and all_tag_re.search(search_block):
                    pairs = [(search_block, replace_block if replace_block is not None else "")]
                elif search_block is None or replace_block is None:
                    return CommandResult(
                        tag=self.metadata.tag,
                        success=False,
                        target_path=norm_rel,
                        message=f"Both <{search_key}> and <{replace_key}> blocks are required for selective editing."
                    )
                else:
                    pairs = [(search_block, replace_block)]

            has_crlf = "\r\n" in original_content

            # 1. Режим полной перезаписи файла (<all />)
            if len(pairs) == 1 and all_tag_re.search(pairs[0][0]):
                new_content = _strip_xml_tag_newlines(pairs[0][1])
                norm_new = new_content.replace("\r\n", "\n")
                final_content = norm_new.replace("\n", "\r\n") if has_crlf else norm_new

                with open(abs_path, "w", encoding="utf-8", newline="") as f:
                    f.write(final_content)

                return CommandResult(
                    tag=self.metadata.tag,
                    success=True,
                    target_path=norm_rel,
                    message=f"File '{norm_rel}' completely overwritten via full-replacement.",
                    original_snapshot=original_content,
                    new_snapshot=final_content
                )

            norm_working = original_content.replace("\r\n", "\n")
            warnings = []

            for pair_idx, (search_block, replace_block) in enumerate(pairs, start=1):
                clean_search = _strip_xml_tag_newlines(search_block)
                clean_replace = _strip_xml_tag_newlines(replace_block)

                if not clean_search:
                    return CommandResult(
                        tag=self.metadata.tag,
                        success=False,
                        target_path=norm_rel,
                        message=f"Empty <{search_key}> block is not allowed in selective editing.",
                        original_snapshot=original_content,
                    )

                norm_search = clean_search.replace("\r\n", "\n")
                norm_replace = clean_replace.replace("\r\n", "\n")

                new_norm_content = None

                # Попытка 1: Прямое точное вхождение
                if norm_search in norm_working:
                    if norm_search and norm_working.count(norm_search) > 1:
                        warnings.append(f"block #{pair_idx}: multiple exact matches, replaced first")
                    new_norm_content = norm_working.replace(norm_search, norm_replace, 1)
                else:
                    # Попытка 2: Сопоставление с игнорированием хвостовых пробелов в строках
                    orig_lines = norm_working.split("\n")
                    search_lines = [line.rstrip() for line in norm_search.split("\n")]

                    matches_indices = []
                    window_size = len(search_lines)

                    for i in range(len(orig_lines) - window_size + 1):
                        current_slice = [line.rstrip() for line in orig_lines[i : i + window_size]]
                        if current_slice == search_lines:
                            matches_indices.append(i)

                    if matches_indices:
                        if len(matches_indices) > 1:
                            warnings.append(f"block #{pair_idx}: multiple trimmed matches, replaced first")
                        matched_idx = matches_indices[0]
                        prefix = orig_lines[:matched_idx]
                        suffix = orig_lines[matched_idx + window_size:]
                        replacement_lines = [] if norm_replace == "" else norm_replace.split("\n")
                        new_norm_content = "\n".join(prefix + replacement_lines + suffix)

                if new_norm_content is None:
                    return CommandResult(
                        tag=self.metadata.tag,
                        success=False,
                        target_path=norm_rel,
                        message="Search block not found in target file.",
                        original_snapshot=original_content,
                        details={
                            "search_block": clean_search,
                            "replace_block": clean_replace,
                        }
                    )

                norm_working = new_norm_content

            # Возвращаем родные CRLF, если они были в файле
            final_content = norm_working.replace("\n", "\r\n") if has_crlf else norm_working

            with open(abs_path, "w", encoding="utf-8", newline="") as f:
                f.write(final_content)

            msg = f"File '{norm_rel}' successfully patched."
            if warnings:
                msg += f" (Warning: {'; '.join(warnings)})"

            return CommandResult(
                tag=self.metadata.tag,
                success=True,
                target_path=norm_rel,
                message=msg,
                original_snapshot=original_content,
                new_snapshot=final_content,
                details={"warnings": warnings} if warnings else {}
            )
        except (SecurityException, AccessDeniedException):
            raise
        except Exception as e:
            return CommandResult(
                tag=self.metadata.tag,
                success=False,
                target_path=rel_path,
                message=f"Edit operation failed: {str(e)}"
            )