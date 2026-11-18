"""Helpers for the specific ARM64 Mach-O and NIBArchive resources in Workbench 8.0.47."""

import struct


def cstrings(data):
    """Yield file offsets and bytes from Mach-O __cstring sections."""
    if len(data) < 32 or struct.unpack_from("<II", data) != (0xFEEDFACF, 0x0100000C):
        raise ValueError("需要 ARM64 Mach-O 资源。")
    command_count = struct.unpack_from("<I", data, 16)[0]
    command_offset = 32
    for _ in range(command_count):
        command, command_size = struct.unpack_from("<II", data, command_offset)
        if command_size < 8 or command_offset + command_size > len(data):
            raise ValueError("Mach-O 加载命令无效。")
        if command == 0x19:  # LC_SEGMENT_64
            section_count = struct.unpack_from("<I", data, command_offset + 64)[0]
            for index in range(section_count):
                section = command_offset + 72 + 80 * index
                name = data[section:section + 16].split(b"\0", 1)[0]
                if name != b"__cstring":
                    continue
                size = struct.unpack_from("<Q", data, section + 40)[0]
                start = struct.unpack_from("<I", data, section + 48)[0]
                limit = start + size
                if limit > len(data):
                    raise ValueError("Mach-O 字符串节越界。")
                while start < limit:
                    end = data.find(b"\0", start, limit)
                    if end < 0:
                        raise ValueError("Mach-O 字符串缺少结束符。")
                    yield start, bytes(data[start:end])
                    start = end + 1
        command_offset += command_size


def patch_cstrings(data, replacements):
    """Keep the original string addresses and section sizes."""
    result = bytearray(data)
    found = set()
    for offset, value in cstrings(data):
        text = value.decode("utf-8", errors="replace")
        if text not in replacements:
            continue
        translated = replacements[text].encode("utf-8")
        if b"\0" in translated or len(translated) > len(value):
            raise ValueError("译文超出原生字符串可用长度 " + repr(text))
        result[offset:offset + len(value)] = translated.ljust(len(value), b"\0")
        found.add(text)
    missing = set(replacements) - found
    if missing:
        raise ValueError("未找到原生显示文本 " + repr(sorted(missing)))
    return bytes(result)


def read_varint(data, offset):
    value = 0
    shift = 0
    while offset < len(data) and shift <= 63:
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if byte & 0x80:
            return value, offset
        shift += 7
    raise ValueError("NIBArchive 变长整数无效。")


def write_varint(value):
    result = bytearray()
    while value >= 128:
        result.append(value & 0x7F)
        value >>= 7
    result.append(value | 0x80)
    return bytes(result)


def nib_values(data):
    """Yield the value records and validate the class-table boundary."""
    if data[:10] != b"NIBArchive":
        raise ValueError("需要 NIBArchive 界面资源。")
    header = struct.unpack_from("<10I", data, 10)
    cursor = header[7]
    widths = {0: 1, 1: 2, 2: 4, 3: 8, 4: 0, 5: 0, 6: 4, 7: 8, 9: 0, 10: 4}
    for _ in range(header[6]):
        key, cursor = read_varint(data, cursor)
        kind = data[cursor]
        cursor += 1
        length_offset = cursor
        if kind == 8:
            size, cursor = read_varint(data, cursor)
        elif kind in widths:
            size = widths[kind]
        else:
            raise ValueError("未知的 NIBArchive 值类型。")
        start = cursor
        cursor += size
        if cursor > header[9]:
            raise ValueError("NIBArchive 值越界。")
        yield key, kind, length_offset, start, cursor
    if cursor != header[9]:
        raise ValueError("NIBArchive 类表位置不一致。")


def patch_nib(data, translations):
    """Update NSString data lengths and the class-table offset."""
    edits = []
    found = set()
    for _, kind, length_offset, start, end in nib_values(data):
        if kind != 8:
            continue
        text = data[start:end].decode("utf-8", errors="replace")
        if text in translations:
            translated = translations[text].encode("utf-8")
            edits.append((length_offset, end, write_varint(len(translated)) + translated))
            found.add(text)
    if found != set(translations):
        raise ValueError("未找到预期的结果区标题。")
    delta = sum(len(value) - (end - start) for start, end, value in edits)
    class_offset = struct.unpack_from("<I", data, 46)[0]
    result = data
    for start, end, value in reversed(edits):
        result = result[:start] + value + result[end:]
    result = bytearray(result)
    struct.pack_into("<I", result, 46, class_offset + delta)
    list(nib_values(result))
    return bytes(result)
