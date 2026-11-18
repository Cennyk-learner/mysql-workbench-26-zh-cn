"""Build the menu, Python presentation, native-label and font patches."""

import ast
import json
import xml.etree.ElementTree as ET

from formats import patch_cstrings, patch_nib


MENU = "Contents/Resources/data/main_menu.xml"
BINDINGS = "Contents/Resources/libraries/mforms.py"
ADMIN = "Contents/Resources/plugins/wb_admin_grt.py"
NIB = "Contents/Resources/WBSQLQueryPanel.nib"
PRIVATE = "Contents/Frameworks/libwbprivate.be.dylib"
PUBLIC = "Contents/Frameworks/libwbpublic.be.dylib"
HELPER = "Contents/Resources/libraries/workbench/zh_cn_ui.py"


def patch_menu(data, translations):
    root = ET.fromstring(data)
    found = set()
    for item in root.iter("value"):
        identifier = item.get("id")
        if item.get("struct-name") != "app.MenuItem" or identifier not in translations:
            continue
        caption = item.find("./value[@key='caption']")
        if caption is None:
            raise ValueError("菜单缺少标题 " + identifier)
        caption.text = translations[identifier]
        accessible = item.find("./value[@key='accessibilityName']")
        if accessible is not None:
            accessible.text = caption.text.replace("_", "").replace("&", "")
        found.add(identifier)
    if found != set(translations):
        raise ValueError("菜单条目与词条不匹配。")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def patch_bindings(data):
    code = data.decode("utf-8")
    calls = {
        "new_Label": [0], "Label_set_text": [1], "Button_set_text": [1],
        "Form_set_title": [1], "Panel_set_title": [1], "AppView_set_title": [1],
        "MenuItem_set_title": [1], "ToolBarItem_set_text": [1], "View_set_tooltip": [1],
        "TabView_add_page": [2], "TabView_set_tab_title": [2], "TreeView_add_column": [2],
        "TaskSidebar_add_section_entry": [4], "TaskSidebar_set_section_entry_text": [2],
    }
    offsets = [0]
    for line in data.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    edits = []
    for node in ast.walk(ast.parse(code)):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if not isinstance(node.func.value, ast.Name) or node.func.value.id != "_mforms":
            continue
        for index in calls.get(node.func.attr, []):
            argument = node.args[index]
            start = offsets[argument.lineno - 1] + argument.col_offset
            end = offsets[argument.end_lineno - 1] + argument.end_col_offset
            edits.append((start, end, b"_zh_text(" + data[start:end] + b")"))
    if len(edits) != 14:
        raise ValueError("Python 界面接口与预期不一致。")
    result = data
    for start, end, value in sorted(edits, reverse=True):
        result = result[:start] + value + result[end:]
    result = b"from workbench.zh_cn_ui import translate as _zh_text\n" + result
    compile(result, BINDINGS, "exec")
    return result


def replace_once(text, original, translated):
    if text.count(original) != 1:
        raise ValueError("未找到唯一的界面位置 " + original)
    return text.replace(original, translated)


def patch_admin(data):
    code = data.decode("utf-8")
    for original, translated in [
        ('"Management", "Management", "MANAGEMENT"', '"Management", "Management", "管理"'),
        ('"Instance", "Instance", "INSTANCE"', '"Instance", "Instance", "实例"'),
        ('"Performance", "Performance", "PERFORMANCE"', '"Performance", "Performance", "性能"'),
        ('"Administration - %s" % title', '"管理 - %s" % title'),
    ]:
        code = replace_once(code, original, translated)
    declaration = "    def register_page(self, page_class, section_id, title, accessibilityName, needs_remote_access=False):\n"
    code = replace_once(code, declaration, declaration + "        title = _zh_text(title)\n")
    code = "from workbench.zh_cn_ui import translate as _zh_text\n" + code
    compile(code, ADMIN, "exec")
    return code.encode("utf-8")


def build(resources, translations):
    helper = (
        '"""Simplified Chinese labels for Workbench 8.0.47."""\n\nTRANSLATIONS = '
        + json.dumps(translations["ui"], ensure_ascii=False, indent=4)
        + "\n\ndef translate(text):\n    return TRANSLATIONS.get(text, text)\n"
    ).encode("utf-8")
    compile(helper, HELPER, "exec")
    native = dict(translations["native"], **{"Lucida Grande": "PingFang SC"})
    return {
        MENU: patch_menu(resources[MENU], translations["menus"]),
        BINDINGS: patch_bindings(resources[BINDINGS]),
        ADMIN: patch_admin(resources[ADMIN]),
        NIB: patch_nib(resources[NIB], {
            "Action Output": "执行输出", "Text Output": "文本输出",
            "Time": "时间", "Action": "操作", "Response": "响应",
            "Duration / Fetch Time": "耗时 / 读取时间",
        }),
        PRIVATE: patch_cstrings(resources[PRIVATE], native),
        PUBLIC: patch_cstrings(resources[PUBLIC], {"Lucida Grande": "PingFang SC"}),
        HELPER: helper,
    }
