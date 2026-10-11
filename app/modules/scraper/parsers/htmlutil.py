import re

from selectolax.lexbor import LexborHTMLParser


def page_lines(html: str) -> list[str]:
    tree = LexborHTMLParser(html)
    for node in tree.css("style, script"):
        node.decompose()
    text = tree.body.text(separator="\n") if tree.body is not None else ""
    text = text.replace("\xa0", " ")
    lines: list[str] = []
    for raw in text.splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if line:
            lines.append(line)
    return lines


def cell_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
