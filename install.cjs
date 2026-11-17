#!/usr/bin/env node
"use strict";

const { spawnSync } = require("node:child_process");
const { createHash } = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { parseArgs } = require("node:util");

const version = "26.10.0";
const productName = "MySQL Workbench 中文版";
const bundleId = "org.workbench-zh-cn.mysqlworkbench";
const oracleSignature = '=identifier "com.oracle.mysqlworkbench" and anchor apple generic'
    + ' and certificate leaf[subject.OU] = "VB5E2TV963"';
const appRoot = "Contents/Resources/app";
const main = "src/main.cjs";
const pkg = "package.json";
const html = "frontend/build/index.html";
const host = "frontend/build/assets/ApplicationHost-D33SUf5-.js";
const index = "frontend/build/assets/index-CLPylcDN.js";
const digests = {
    [main]: "501c9cc3103a194a8c719a5125077dd01ad3d18c0adedbaa59f39145a0dbdded",
    [pkg]: "dea269a90d8043deca486ec11e02c2f55b3c7f74b9d9761423985a84cd700aa8",
    [html]: "ab7de99dcbb14ec4452372c831582a44d00543a0fb9ed63c241b825afd0c2eac",
    [host]: "d9dc0516512493f62b28b5afe7067b51e10ff53ad125a239a0a374d1d49b9035",
    [index]: "7b36b18556cff918e1b85774c1c85d6f868375ff83e5d4736328ac9da38762e6",
};
const displayProperties = new Set([
    "advancedActionCaption", "aria-label", "caption", "children", "data-tooltip",
    "description", "label", "message", "placeholder", "prompt", "text", "title", "tooltip",
]);
const nativeRoles = {
    undo: "撤销", redo: "重做", cut: "剪切", copy: "复制", paste: "粘贴",
    delete: "删除", selectAll: "全选", toggleDevTools: "切换开发者工具",
    togglefullscreen: "切换全屏", minimize: "最小化", zoom: "缩放", front: "将全部窗口置于前台",
    close: "关闭", services: "服务", hide: "隐藏 MySQL Workbench", hideOthers: "隐藏其他应用",
    unhide: "显示全部", quit: "退出 MySQL Workbench",
};

function run(command, args, options = {}) {
    const result = spawnSync(command, args, { encoding: "utf8", ...options });
    if (result.error) throw result.error;
    if (result.status !== 0) {
        throw new Error((result.stderr || result.stdout || command).trim());
    }
    return result.stdout.trim();
}

function readTranslations() {
    const filename = path.join(__dirname, "界面词条.tsv");
    const translations = new Map();
    for (const line of fs.readFileSync(filename, "utf8").split(/\r?\n/)) {
        if (!line || line.startsWith("#")) continue;
        const [english, chinese, extra] = line.split("\t");
        if (!english || !chinese || extra !== undefined || translations.has(english)) {
            throw new Error("词条格式错误或重复 " + english);
        }
        translations.set(english, chinese);
    }
    return translations;
}

function readResources(source) {
    const plist = path.join(source, "Contents/Info.plist");
    const detected = run("/usr/libexec/PlistBuddy", ["-c", "Print :CFBundleShortVersionString", plist]);
    if (detected !== version) {
        throw new Error("此补丁适用于 Workbench " + version + "，检测到 " + detected);
    }

    return new Map(Object.entries(digests).map(([file, expected]) => {
        const bytes = fs.readFileSync(path.join(source, appRoot, file));
        const actual = createHash("sha256").update(bytes).digest("hex");
        if (actual !== expected) {
            throw new Error("资源与已验证版本不一致 " + file);
        }
        return [file, bytes.toString("utf8")];
    }));
}

function replaceOnce(source, before, after) {
    const start = source.indexOf(before);
    if (start < 0 || start !== source.lastIndexOf(before)) {
        throw new Error("补丁定位失败 " + before);
    }
    return source.slice(0, start) + after + source.slice(start + before.length);
}

function propertyName(property) {
    return property?.key?.name ?? property?.key?.value;
}

function isDialogCall(call, node) {
    const method = call?.callee?.property?.name;
    return call?.type === "CallExpression"
        && ["showInformationMessage", "showErrorMessage", "showWarningMessage"].includes(method)
        && call.arguments[0] === node;
}

function isDisplayLiteral(node, parents) {
    const parent = parents.at(-2);
    const grandparent = parents.at(-3);
    if (parent?.type === "Property" && parent.value === node) {
        return displayProperties.has(propertyName(parent));
    }
    if (parent?.type === "ArrayExpression" && grandparent?.type === "Property") {
        return propertyName(grandparent) === "children";
    }
    if (parent?.type === "ConditionalExpression" && parent.test !== node) {
        return (grandparent?.type === "Property" && displayProperties.has(propertyName(grandparent)))
            || isDialogCall(grandparent, parent);
    }
    return isDialogCall(parent, node);
}

function localizeRenderer(source, translations, updated) {
    // Node bundles Acorn. It is used only by the installer to locate string literals in the compiled UI.
    const { parse } = require("internal/deps/acorn/acorn/dist/acorn");
    const { fullAncestor } = require("internal/deps/acorn/acorn-walk/dist/walk");
    const ast = parse(source, { ecmaVersion: "latest", sourceType: "module" });
    const edits = [];
    fullAncestor(ast, (node, _, parents) => {
        if (node.type === "Literal" && typeof node.value === "string" && isDisplayLiteral(node, parents)) {
            const translated = translations.get(node.value);
            if (translated !== undefined) {
                edits.push({ start: node.start, end: node.end, text: JSON.stringify(translated) });
                updated.add(node.value);
            }
        } else if (node.type === "TemplateLiteral" && isDialogCall(parents.at(-2), node)) {
            const opening = node.quasis[0];
            const translated = translations.get(opening.value.cooked);
            if (translated !== undefined) {
                const text = translated.replaceAll("\\", "\\\\").replaceAll("`", "\\`").replaceAll("${", "\\${");
                edits.push({ start: opening.start, end: opening.end, text });
                updated.add(opening.value.cooked);
            }
        }
    });

    let result = source;
    for (const edit of edits.sort((a, b) => b.start - a.start)) {
        result = result.slice(0, edit.start) + edit.text + result.slice(edit.end);
    }

    const progress = "Session created, opening new connection...";
    const progressCall = 'e("' + progress + '")';
    const hasProgress = result.includes(progressCall) && translations.has(progress);
    if (hasProgress) {
        result = replaceOnce(result, progressCall, "e(" + JSON.stringify(translations.get(progress)) + ")");
        updated.add(progress);
    }

    parse(result, { ecmaVersion: "latest", sourceType: "module" });
    return { result, count: edits.length + Number(hasProgress) };
}

function localizeMain(source) {
    source = replaceOnce(source, 'const fs = require("fs");', [
        'const { localizeMenu } = require("./workbench-zh-cn.cjs");',
        'const fs = require("fs");',
    ].join("\n"));
    return replaceOnce(
        source,
        "return Menu.buildFromTemplate(template);",
        "return Menu.buildFromTemplate(localizeMenu(template, new Set(recentFiles)));",
    );
}

function nativeMenuModule(translations) {
    return '"use strict";\n\n'
        + "const translations = new Map(" + JSON.stringify([...translations], null, 4) + ");\n"
        + "const roles = " + JSON.stringify(nativeRoles, null, 4) + ";\n\n"
        + [
            "function localizeMenu(items, fileLabels) {",
            "    return items.map((item) => {",
            "        const result = { ...item };",
            "        if (typeof item.label === 'string' && !fileLabels.has(item.label)) {",
            "            result.label = translations.get(item.label) ?? item.label;",
            "        } else if (item.role && Object.hasOwn(roles, item.role)) {",
            "            result.label = roles[item.role];",
            "        }",
            "        if (Array.isArray(item.submenu)) {",
            "            result.submenu = localizeMenu(item.submenu, fileLabels);",
            "        }",
            "        return result;",
            "    });",
            "}",
            "",
            "module.exports = { localizeMenu };",
            "",
        ].join("\n");
}

function prepare(source) {
    const translations = readTranslations();
    const resources = readResources(source);
    const updates = new Set();
    const patched = new Map();
    let count = 0;
    for (const file of [host, index]) {
        const renderer = localizeRenderer(resources.get(file), translations, updates);
        patched.set(file, renderer.result);
        count += renderer.count;
    }

    // Guard the most important surfaces in addition to checking the source fingerprints.
    for (const required of ["DATABASE CONNECTIONS", "CONNECTIONS", "Test Connection",
        "Default Schema", "Preferences", "New SQL Script", "Run Current Statement", "Results"]) {
        if (!updates.has(required)) throw new Error("没有定位到界面词条 " + required);
    }

    const metadata = JSON.parse(resources.get(pkg));
    metadata.productName = productName;
    patched.set(pkg, JSON.stringify(metadata, null, 4) + "\n");
    patched.set(main, localizeMain(resources.get(main)));
    patched.set("src/workbench-zh-cn.cjs", nativeMenuModule(translations));
    patched.set(html, replaceOnce(resources.get(html), '<html lang="en">', '<html lang="zh-CN">'));
    console.log("Workbench " + version + " 校验通过，前端定位到 " + updates.size
        + " 个不同词条，共 " + count + " 处替换。");
    return patched;
}

function install(source, destination, patched) {
    if (path.extname(destination) !== ".app" || fs.existsSync(destination)) {
        throw new Error("安装目标须为尚不存在的 .app 路径 " + destination);
    }

    const parent = path.dirname(destination);
    fs.mkdirSync(parent, { recursive: true });
    const stage = fs.mkdtempSync(path.join(parent, ".workbench-zh-"));
    try {
        const copy = path.join(stage, path.basename(destination));
        // Create a local build from the verified resources and sign only its outer bundle.
        run("/usr/bin/ditto", ["--noqtn", source, copy]);
        run("/usr/bin/codesign", ["--verify", "--deep", "--strict", "-R", oracleSignature, copy]);
        for (const [file, text] of patched) {
            fs.writeFileSync(path.join(copy, appRoot, file), text, "utf8");
        }

        const plist = path.join(copy, "Contents/Info.plist");
        // Electron uses CFBundleName when looking up its existing helper executables.
        for (const [key, value] of Object.entries({
            CFBundleIdentifier: bundleId,
            CFBundleDisplayName: productName,
        })) {
            run("/usr/libexec/PlistBuddy", ["-c", "Set :" + key + " " + value, plist]);
        }

        run(process.execPath, ["--check", path.join(copy, appRoot, main)]);
        run(process.execPath, ["--check", path.join(copy, appRoot, "src/workbench-zh-cn.cjs")]);
        run("/usr/bin/codesign", [
            "--force", "--sign", "-", "--options", "runtime",
            "--preserve-metadata=entitlements", copy,
        ]);
        run("/usr/bin/codesign", ["--verify", "--deep", "--strict", copy]);
        const launcher = path.join(copy, "Contents/MacOS/MySQL Workbench");
        if (run(launcher, ["--version"], { timeout: 15000 }) !== productName + " " + version) {
            throw new Error("中文版启动检查失败。");
        }

        if (fs.existsSync(destination)) throw new Error("安装目录已有同名应用 " + destination);
        fs.renameSync(copy, destination);
        console.log("中文版已安装 " + destination);
    } finally {
        fs.rmSync(stage, { recursive: true, force: true });
    }
}

try {
    const { values } = parseArgs({
        options: { source: { type: "string" }, dest: { type: "string" }, check: { type: "boolean" } },
    });
    if (process.platform !== "darwin" || process.arch !== "arm64") {
        throw new Error("此补丁需要在 Apple 芯片 Mac 上运行原生 arm64 版 Node.js。");
    }
    const source = fs.realpathSync(values.source ?? "/Applications/MySQL Workbench.app");
    const destination = path.resolve(values.dest ?? path.join(os.homedir(), "Applications", productName + ".app"));
    const patched = prepare(source);
    if (!values.check) install(source, destination, patched);
} catch (error) {
    console.error("安装中止 " + error.message);
    process.exitCode = 1;
}
