import re
import os


class XMLCodeParser:
    @staticmethod
    def normalize_path(path_str):
        path_str = path_str.strip().replace('/', os.sep).replace('\\', os.sep)
        return path_str

    @classmethod
    def parse(cls, raw_xml):
        instructions = []

        # Регулярка для <fs_create path="...">...</fs_create>
        create_pattern = r'<fs_create\s+path=["\'](.*?)["\']\s*>(.*?)</fs_create>'
        for match in re.finditer(create_pattern, raw_xml, re.DOTALL):
            rel_path = cls.normalize_path(match.group(1))
            content = match.group(2).strip('\r\n')
            instructions.append({
                'type': 'create',
                'path': rel_path,
                'content': content
            })

        # Регулярка для <fs_edit path="...">...</fs_edit>
        edit_pattern = r'<fs_edit\s+path=["\'](.*?)["\']\s*>(.*?)</fs_edit>'
        for match in re.finditer(edit_pattern, raw_xml, re.DOTALL):
            rel_path = cls.normalize_path(match.group(1))
            inner = match.group(2)

            search_match = re.search(r'<fs_search>(.*?)</fs_search>', inner, re.DOTALL)
            replace_match = re.search(r'<fs_replace>(.*?)</fs_replace>', inner, re.DOTALL)

            if search_match and replace_match:
                search_code = search_match.group(1).strip('\r\n')
                replace_code = replace_match.group(1).strip('\r\n')

                is_replace_all = '<all />' in search_code or '<all/>' in search_code

                instructions.append({
                    'type': 'edit',
                    'path': rel_path,
                    'search': search_code,
                    'replace': replace_code,
                    'replace_all': is_replace_all
                })

        return instructions