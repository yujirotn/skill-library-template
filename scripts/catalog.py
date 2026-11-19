"""Build CATALOG.md from the name and description in each skill's front matter."""

import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
FIELD = re.compile(r"^(name|description):[ \t]*(.*)$")
MARKDOWN_ESCAPES = str.maketrans({character: "\\" + character for character in "\\|*_~`[]"})


def read_fields(path):
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("先頭に --- で囲った name と description が必要です")
    end = next((index for index, line in enumerate(lines[1:], 1) if line.rstrip() == "---"), None)
    if end is None:
        raise ValueError("先頭の項目を --- で閉じてください")

    fields = {}
    for index, line in enumerate(lines[1:end], 1):
        match = FIELD.fullmatch(line)
        if not match:
            continue
        key, first = match.groups()
        if key in fields:
            raise ValueError(f"{key} が重複しています")
        continuation = []
        for following in lines[index + 1 : end]:
            if following and not following[0].isspace():
                break
            continuation.append(following.strip())
        fields[key] = read_scalar(first, continuation)

    if not fields.get("name") or not fields.get("description"):
        raise ValueError("name と description に値を入れてください")
    if fields["name"] != path.parent.name or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", fields["name"]):
        raise ValueError("name とフォルダ名を同じ半角英小文字・数字・ハイフンにしてください")
    return fields["name"], fields["description"]


def read_scalar(first, continuation):
    if re.fullmatch(r"[>|](?:[1-9][+-]?|[+-][1-9]?)?(?:[ \t]+#.*)?", first.strip()):
        value = " ".join(continuation)
    else:
        value = " ".join([first, *continuation]).strip()
        if value.startswith('"'):
            decoded, end = json.JSONDecoder().raw_decode(value)
            if not re.fullmatch(r"\s*(?:#.*)?", value[end:]):
                raise ValueError("二重引用符の後はコメントだけを書けます")
            value = decoded
        elif value.startswith("'"):
            match = re.fullmatch(r"'((?:[^']|'')*)'\s*(?:#.*)?", value)
            if not match:
                raise ValueError("一重引用符を閉じてください。文中の一重引用符は2つ重ねます")
            value = match.group(1).replace("''", "'")
        else:
            value = re.split(r"(?:^|\s)#", value, maxsplit=1)[0]
    return " ".join(value.split())


def table_text(value):
    # Keep descriptions and member names as literal text inside Markdown cells.
    return html.escape(value, quote=False).replace("\n", " ").translate(MARKDOWN_ESCAPES)


def main():
    rows = [
        "# スキル一覧",
        "",
        "この一覧は SKILL.md から生成しています。更新するには `python3 scripts/catalog.py` を実行します。",
        "",
        "| スキル名 | 持ち主 | 一言 | 場所 |",
        "| --- | --- | --- | --- |",
    ]
    skills = sorted((ROOT / "members").glob("*/skills/*/SKILL.md"))
    for path in skills:
        relative = path.relative_to(ROOT)
        owner = relative.parts[1]
        if owner == "_ひな形":
            continue
        try:
            if any(part.is_symlink() for part in (path, path.parent, path.parent.parent, path.parent.parent.parent)):
                raise ValueError("シンボリックリンクは使えません")
            name, description = read_fields(path)
        except (OSError, ValueError) as error:
            sys.exit(f"{relative.as_posix()}: {error}")
        link = f"[SKILL.md]({quote(relative.as_posix())})"
        rows.append(f"| {table_text(name)} | {table_text(owner)} | {table_text(description)} | {link} |")

    (ROOT / "CATALOG.md").write_text("\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
