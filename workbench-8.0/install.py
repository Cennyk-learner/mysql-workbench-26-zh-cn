#!/usr/bin/env python3
"""Install or restore the Workbench 8.0.47 ARM64 Chinese UI patch."""

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import shutil
import subprocess
import sys
import tempfile

from patch_resources import ADMIN, BINDINGS, HELPER, MENU, NIB, PRIVATE, PUBLIC, build


VERSION = "8.0.47.CE"
PATCH_VERSION = 1
MARKER = "Contents/Resources/workbench-zh-cn.json"
INFO = "Contents/Info.plist"
EXECUTABLE = "Contents/MacOS/MySQLWorkbench"
SIGNATURE = "Contents/_CodeSignature/CodeResources"
DIGESTS = {
    MENU: "9483f01a53f0ad56c9bb535d31b8166f86ca482b71ebe1f48a1281fa8a437b4a",
    BINDINGS: "902623fdfaf19a3488f0e1080027dbf0ee73148f8b664229be89935f6b58c95a",
    ADMIN: "995611aea6e2ebb8565c742a204f5b41f1f5606015a97dab83500e851e068036",
    NIB: "8123bdbc399358b1bb3feda844595b0b4bec7d5006e692f1fe7bb73d90aaebab",
    PRIVATE: "c43d32d66d66de52dc5bb86a6787da2e6d71efefcc96832f3a4838b63f9c9469",
    PUBLIC: "90acc7ad5200310fbc626b2fc352196b42cce8cc1fb48e7417d368545d9a31f2",
}
ORIGINAL_FILES = list(DIGESTS) + [INFO, EXECUTABLE, SIGNATURE]
CREATED_FILES = [HELPER, MARKER]
ORACLE_REQUIREMENT = (
    '=identifier "com.oracle.workbench.MySQLWorkbench" and anchor apple generic'
    ' and certificate leaf[subject.OU] = "VB5E2TV963"'
)


def run(arguments, **kwargs):
    result = subprocess.run(arguments, capture_output=True, text=True, **kwargs)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout or str(arguments[0])).strip())
    return result.stdout.strip()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def app_file(app, relative):
    result = app / relative
    if not result.resolve().is_relative_to(app):
        raise ValueError("应用资源路径越界 " + relative)
    return result


def atomic_write(destination, data):
    mode = destination.stat().st_mode & 0o777 if destination.exists() else 0o644
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(data)
            stream.flush()
            os.fchmod(stream.fileno(), mode)
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)


def validate_version(app):
    with app_file(app, INFO).open("rb") as stream:
        info = plistlib.load(stream)
    if info.get("CFBundleShortVersionString") != VERSION:
        raise ValueError("此补丁适用于 Workbench 8.0.47 CE。")
    if info.get("CFBundleIdentifier") != "com.oracle.workbench.MySQLWorkbench":
        raise ValueError("应用标识与官方 Workbench 8.0 不一致。")
    return info


def ensure_closed(app):
    command = str(app_file(app, EXECUTABLE))
    processes = run(["/bin/ps", "-axo", "comm="]).splitlines()
    if command in processes:
        raise RuntimeError("请保存 SQL 并退出 Workbench，再运行安装或恢复命令。")


def check_original(app):
    resources = {}
    for relative, expected in DIGESTS.items():
        data = app_file(app, relative).read_bytes()
        if sha256(data) != expected:
            raise ValueError("资源与官方 8.0.47 ARM64 安装包不一致 " + relative)
        resources[relative] = data
    # Verify the original executable identity. Generated Python caches are handled
    # separately because they can change the framework resource seal after launch.
    run([
        "/usr/bin/codesign", "--verify", "--ignore-resources",
        "-R", ORACLE_REQUIREMENT, str(app),
    ])
    return resources


def installed_manifest(app):
    marker = app_file(app, MARKER)
    if not marker.exists():
        return None
    metadata = json.loads(marker.read_text(encoding="utf-8"))
    if metadata.get("version") != VERSION or metadata.get("patch_version") != PATCH_VERSION:
        raise ValueError("检测到不同版本的中文补丁。")
    backup = Path(metadata["backup"]).expanduser().resolve()
    manifest = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("app") != str(app):
        raise ValueError("备份与当前应用路径不匹配。")
    if set(manifest.get("original", {})) != set(ORIGINAL_FILES):
        raise ValueError("备份文件清单不完整。")
    if set(manifest.get("installed", {})) != set(ORIGINAL_FILES + CREATED_FILES):
        raise ValueError("已安装文件清单不完整。")
    for relative, digest in manifest["installed"].items():
        if sha256(app_file(app, relative).read_bytes()) != digest:
            raise ValueError("安装后资源已变化，请保留备份并重新核对 " + relative)
    for relative, digest in manifest["original"].items():
        candidate = backup / relative
        if not candidate.resolve().is_relative_to(backup):
            raise ValueError("备份资源路径越界。")
        if sha256(candidate.read_bytes()) != digest:
            raise ValueError("原版备份校验失败 " + relative)
    return backup, manifest


def rollback(app, backup):
    for relative in ORIGINAL_FILES:
        atomic_write(app_file(app, relative), (backup / relative).read_bytes())
    for relative in CREATED_FILES:
        app_file(app, relative).unlink(missing_ok=True)


def archive_generated_cache(app, backup):
    framework = app / "Contents/Frameworks/Python.framework/Versions/3.12"
    with (framework / "_CodeSignature/CodeResources").open("rb") as stream:
        known = plistlib.load(stream)["files2"]
    with (backup / SIGNATURE).open("rb") as stream:
        application_files = plistlib.load(stream)["files2"]
    candidates = [
        cache for cache in (framework / "lib/python3.12").rglob("*.pyc")
        if str(cache.relative_to(framework)) not in known
    ]
    candidates.extend(
        cache for cache in (app / "Contents/Resources").rglob("*.pyc")
        if str(cache.relative_to(app / "Contents")) not in application_files
    )
    count = 0
    for cache in candidates:
        destination = backup / "generated-cache" / cache.relative_to(app)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(cache), str(destination))
        count += 1
    return count


def register(app):
    run([
        "/System/Library/Frameworks/CoreServices.framework/Frameworks/"
        "LaunchServices.framework/Support/lsregister", "-f", str(app),
    ])


def install(app, info, patched):
    ensure_closed(app)
    for relative in CREATED_FILES:
        if app_file(app, relative).exists():
            raise ValueError("目标资源已存在 " + relative)
    backup_root = Path.home() / "Library/Application Support/MySQL/Workbench/zh-cn-backups"
    backup_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-")
    backup = Path(tempfile.mkdtemp(prefix=VERSION + "-" + stamp, dir=backup_root))
    manifest = {"app": str(app), "original": {}, "installed": {}}
    for relative in ORIGINAL_FILES:
        source = app_file(app, relative)
        destination = backup / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        manifest["original"][relative] = sha256(destination.read_bytes())

    try:
        cached = archive_generated_cache(app, backup)
        for relative, content in patched.items():
            atomic_write(app_file(app, relative), content)
        info.setdefault("LSEnvironment", {})["PYTHONDONTWRITEBYTECODE"] = "1"
        atomic_write(app_file(app, INFO), plistlib.dumps(info, sort_keys=False))
        marker = {
            "version": VERSION, "patch_version": PATCH_VERSION, "backup": str(backup),
        }
        atomic_write(app_file(app, MARKER), json.dumps(marker, ensure_ascii=False).encode("utf-8"))
        for relative in [PRIVATE, PUBLIC]:
            run([
                "/usr/bin/codesign", "--force", "--sign", "-",
                "--preserve-metadata=identifier,entitlements,flags",
                str(app_file(app, relative)),
            ])
        run([
            "/usr/bin/codesign", "--force", "--sign", "-",
            "--preserve-metadata=entitlements,flags", str(app),
        ])
        run(["/usr/bin/codesign", "--verify", "--deep", "--strict", str(app)])
        register(app)
        for relative in ORIGINAL_FILES + CREATED_FILES:
            manifest["installed"][relative] = sha256(app_file(app, relative).read_bytes())
        (backup / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )
    except BaseException:
        rollback(app, backup)
        raise
    print("安装完成，已更新中文界面并应用苹方字体修复。")
    print("归档的运行时缓存", cached, "个。")
    print("原版资源备份", backup)
    print("应用路径", app)


def restore(app, installed):
    ensure_closed(app)
    backup, _ = installed
    rollback(app, backup)
    run(["/usr/bin/codesign", "--verify", "--deep", "--strict", str(app)])
    register(app)
    print("已恢复安装补丁前的应用资源和签名。")
    print("备份保留在", backup)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, default=Path("/Applications/MySQLWorkbench.app"))
    parser.add_argument("--copy-to", type=Path, help="在新路径创建本地汉化副本")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="只校验版本和补丁定位")
    mode.add_argument("--restore", action="store_true", help="恢复此安装器备份的原版资源")
    args = parser.parse_args()
    if args.restore and args.copy_to:
        parser.error("恢复时请用 --app 指定已安装的汉化副本。")
    if sys.platform != "darwin" or platform.machine() != "arm64":
        raise ValueError("需要 Apple 芯片 Mac 和原生 ARM64 Python 3.9 或更新版本。")
    app = args.app.expanduser().resolve(strict=True)
    info = validate_version(app)
    installed = installed_manifest(app)
    if args.restore:
        if installed is None:
            raise ValueError("当前应用没有此安装器创建的补丁记录。")
        restore(app, installed)
        return
    if installed:
        if args.copy_to:
            raise ValueError("请从官方原版创建新的汉化副本。")
        print("已安装此版本的中文界面补丁，资源校验通过。")
        print("原版备份", installed[0])
        return
    resources = check_original(app)
    translations = json.loads(Path(__file__).with_name("translations.json").read_text(encoding="utf-8"))
    patched = build(resources, translations)
    print("8.0.47 ARM64 资源校验通过，菜单、界面与字体补丁定位成功。")
    if args.check:
        return
    if args.copy_to:
        ensure_closed(app)
        destination = args.copy_to.expanduser().resolve()
        if destination.suffix != ".app" or destination.exists():
            raise ValueError("汉化副本需要一个尚不存在的 .app 路径。")
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            # This is a new local build. Keep the bundle layout while avoiding
            # inherited metadata from the original downloaded application.
            run(["/usr/bin/ditto", "--noextattr", "--noqtn", str(app), str(destination)])
            install(destination, info, patched)
        except BaseException:
            shutil.rmtree(destination, ignore_errors=True)
            raise
    else:
        install(app, info, patched)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("操作未完成", str(error), file=sys.stderr)
        sys.exit(1)
