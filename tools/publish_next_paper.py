#!/usr/bin/env python3
"""Audit and publish one queued paper into the static papers reader."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUEUE_DIR = ROOT / "paper_queue"
SOURCE_DIR = QUEUE_DIR / "source"
POOL_PATH = QUEUE_DIR / "pool.json"
ERROR_PATH = QUEUE_DIR / "error_pool.json"
PUBLISHED_PATH = QUEUE_DIR / "published.json"
AUDIT_DIR = QUEUE_DIR / "audit"
POSTS_DIR = ROOT / "source" / "_posts"
IMAGE_OUT_DIR = ROOT / "source" / "images" / "papers"
READER_OUT_DIR = ROOT / "source" / "papers-reader"
READER_PAPERS_DIR = READER_OUT_DIR / "papers"
READER_FIGURES_DIR = READER_OUT_DIR / "figures"
HEXO_LAYOUT_FALSE = "---\nlayout: false\n---\n"

PLACEHOLDERS = (
    "让 Claude",
    "TODO",
    "PLACEHOLDER",
    "undefined",
    "NaN",
    "�",
)

AUDIENCE_LABELS = {
    "A": ("工", "算法工程师"),
    "B": ("学", "冲击算法岗学生"),
    "C": ("师", "大模型方向老师"),
}


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def strip_tags(value: str) -> str:
    value = re.sub(r"<script\b.*?</script>", "", value, flags=re.S | re.I)
    value = re.sub(r"<style\b.*?</style>", "", value, flags=re.S | re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    return html.unescape(re.sub(r"\s+", " ", value)).strip()


def parse_index() -> list[dict]:
    index_html = (SOURCE_DIR / "index_open.html").read_text(encoding="utf-8")
    pattern = re.compile(
        r'<div class="paper"\s+data-tags="(?P<tags>[^"]*)"\s+'
        r'data-aud="(?P<aud>[^"]*)"\s+data-priority="(?P<priority>[^"]*)">'
        r'(?P<body>.*?)<div class="paper-actions">',
        re.S,
    )
    items: list[dict] = []
    seen: set[str] = set()
    for match in pattern.finditer(index_html):
        body = match.group("body")
        title_match = re.search(
            r'<div class="paper-title">\s*<a class="paper-link" href="([^"]+)">(.*?)</a>\s*</div>',
            body,
            re.S,
        )
        arxiv_match = re.search(r'<div class="paper-arxiv">(.*?)</div>', body, re.S)
        note_match = re.search(r'<div class="paper-note">(.*?)</div>', body, re.S)
        if not title_match:
            continue
        href = html.unescape(title_match.group(1))
        slug = Path(href).stem
        if slug in seen:
            continue
        seen.add(slug)
        items.append(
            {
                "slug": slug,
                "href": href,
                "title": strip_tags(title_match.group(2)),
                "arxiv": strip_tags(arxiv_match.group(1)) if arxiv_match else "",
                "tags": [x.strip() for x in match.group("tags").split(",") if x.strip()],
                "audience": [x.strip() for x in match.group("aud").split(",") if x.strip()],
                "priority": match.group("priority").strip(),
                "note": strip_tags(note_match.group(1)) if note_match else "",
            }
        )
    return items


def init_pool(force: bool = False) -> None:
    if POOL_PATH.exists() and not force:
        return
    published = {item["slug"] for item in load_json(PUBLISHED_PATH, [])}
    errors = {item["slug"] for item in load_json(ERROR_PATH, [])}
    pool = [item for item in parse_index() if item["slug"] not in published | errors]
    write_json(POOL_PATH, pool)
    if not ERROR_PATH.exists():
        write_json(ERROR_PATH, [])
    if not PUBLISHED_PATH.exists():
        write_json(PUBLISHED_PATH, [])


def png_dimensions(path: Path) -> tuple[int, int] | None:
    data = path.read_bytes()[:24]
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


def image_refs(paper_html: str) -> list[str]:
    return re.findall(r'<img[^>]+src="(\.\./figures/[^"]+)"', paper_html)


def as_standalone_page(page_html: str) -> str:
    if page_html.startswith(HEXO_LAYOUT_FALSE):
        return page_html
    return HEXO_LAYOUT_FALSE + page_html


def sentence_audit(text: str) -> list[str]:
    issues: list[str] = []
    chunks = re.split(r"(?<=[。！？.!?])\s+", text)
    for idx, sentence in enumerate(chunks, 1):
        s = sentence.strip()
        if not s:
            continue
        for marker in PLACEHOLDERS:
            if marker in s:
                issues.append(f"sentence {idx} contains placeholder marker: {marker}")
        if len(s) > 1200:
            issues.append(f"sentence {idx} is too long for review: {len(s)} chars")
    return issues


def audit(item: dict) -> dict:
    paper_path = SOURCE_DIR / item["href"]
    report = {
        "slug": item["slug"],
        "title": item["title"],
        "status": "ok",
        "errors": [],
        "warnings": [],
        "images": [],
        "sentence_count": 0,
    }
    if not paper_path.exists():
        report["errors"].append(f"missing paper html: {item['href']}")
        report["status"] = "error"
        return report

    paper_html = paper_path.read_text(encoding="utf-8")
    if not item["title"] or not item["arxiv"]:
        report["errors"].append("missing title or arxiv metadata")
    if "paper-sections" not in paper_html or "note-panel" not in paper_html:
        report["errors"].append("missing required paper sections or overview note")
    if not re.search(r"Conclusion|结论|一句话总结", paper_html):
        report["errors"].append("missing clear conclusion marker")

    visible_text = strip_tags(paper_html)
    sentences = [s for s in re.split(r"(?<=[。！？.!?])\s+", visible_text) if s.strip()]
    report["sentence_count"] = len(sentences)
    report["errors"].extend(sentence_audit(visible_text))

    for src in image_refs(paper_html):
        fig_path = (paper_path.parent / src).resolve()
        image_report = {"src": src, "exists": fig_path.exists()}
        if not fig_path.exists():
            report["errors"].append(f"missing image: {src}")
        else:
            dims = png_dimensions(fig_path)
            image_report["bytes"] = fig_path.stat().st_size
            image_report["dimensions"] = list(dims) if dims else None
            if not dims:
                report["errors"].append(f"image is not a valid PNG: {src}")
            elif dims[0] < 320 or dims[1] < 180:
                report["errors"].append(f"image too small to read: {src} {dims[0]}x{dims[1]}")
            elif fig_path.stat().st_size < 4096:
                report["errors"].append(f"image file too small to trust: {src}")
        report["images"].append(image_report)

    if not report["images"]:
        report["warnings"].append("paper has no image gallery")
    if report["errors"]:
        report["status"] = "error"
    return report


def copy_static_paper(item: dict) -> None:
    src_paper = SOURCE_DIR / item["href"]
    READER_PAPERS_DIR.mkdir(parents=True, exist_ok=True)
    page_html = src_paper.read_text(encoding="utf-8")
    (READER_PAPERS_DIR / f"{item['slug']}.html").write_text(
        as_standalone_page(page_html),
        encoding="utf-8",
    )


def copy_static_images(item: dict) -> None:
    paper_path = SOURCE_DIR / item["href"]
    paper_html = paper_path.read_text(encoding="utf-8")
    READER_FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    for src in image_refs(paper_html):
        src_path = (paper_path.parent / src).resolve()
        shutil.copy2(src_path, READER_FIGURES_DIR / Path(src).name)


def div_block_end(text: str, start: int) -> int:
    depth = 0
    token_re = re.compile(r"</?div\b[^>]*>", re.I)
    for match in token_re.finditer(text, start):
        token = match.group(0).lower()
        if token.startswith("</"):
            depth -= 1
            if depth == 0:
                return match.end()
        else:
            depth += 1
    raise ValueError(f"unclosed div block at offset {start}")


def filter_paper_cards(index_html: str, published_slugs: set[str]) -> str:
    out: list[str] = []
    pos = 0
    for match in re.finditer(r'<div class="paper"(?=\s|>)', index_html):
        start = match.start()
        end = div_block_end(index_html, start)
        block = index_html[start:end]
        href_match = re.search(r'href="papers/([^"]+)\.html"', block)
        slug = href_match.group(1) if href_match else ""
        out.append(index_html[pos:start])
        if slug in published_slugs:
            out.append(block)
        pos = end
    out.append(index_html[pos:])
    return "".join(out)


def tag_section_counts(index_html: str) -> dict[str, int]:
    tags = ["数据工程", "CPT", "后训练", "技术报告", "其他"]
    counts: dict[str, int] = {}
    for tag in tags:
        start_pat = f'<div class="tag-section" data-tag="{tag}">'
        start = index_html.find(start_pat)
        if start == -1:
            counts[tag] = 0
            continue
        next_starts = [
            index_html.find(f'<div class="tag-section" data-tag="{other}">', start + 1)
            for other in tags
            if other != tag
        ]
        next_starts = [x for x in next_starts if x != -1]
        end = min(next_starts) if next_starts else index_html.find("<footer>", start)
        section = index_html[start:end]
        counts[tag] = len(re.findall(r'<div class="paper"(?=\s|>)', section))
    return counts


def update_index_counts(index_html: str, published_count: int) -> str:
    counts = tag_section_counts(index_html)
    index_html = re.sub(
        r'<div class="subtitle">.*?</div>',
        f'<div class="subtitle">{published_count} 篇已发布 · 每天 1 篇更新 · 5 标签分类 · 3 类读者推荐路径 · 中英双语全文翻译 · 公式 KaTeX · 图含中文图注</div>',
        index_html,
        count=1,
        flags=re.S,
    )
    for tag, count in counts.items():
        stat_re = re.compile(
            rf'(<div class="stat-card" data-stat="{re.escape(tag)}">.*?<div class="stat-value">)\d+(</div>)',
            re.S,
        )
        index_html = stat_re.sub(rf"\g<1>{count}\2", index_html, count=1)

        section_re = re.compile(
            rf'(<div class="tag-section" data-tag="{re.escape(tag)}">.*?<span class="tag-count">)\d+ 篇(?:主标)?(</span>)',
            re.S,
        )
        index_html = section_re.sub(rf"\g<1>{count} 篇\2", index_html, count=1)
    index_html = re.sub(
        r"<div>v0\.1 · .*? · 中英双语全文 \+ KaTeX 公式 \+ 图含中文图注</div>",
        f"<div>v0.1 · {published_count} 篇已发布 · 每天 1 篇更新 · 中英双语全文 + KaTeX 公式 + 图含中文图注</div>",
        index_html,
        count=1,
    )
    return index_html


def render_static_index(published: list[dict]) -> None:
    published_slugs = {item["slug"] for item in published}
    index_html = (SOURCE_DIR / "index_open.html").read_text(encoding="utf-8")
    index_html = filter_paper_cards(index_html, published_slugs)
    index_html = update_index_counts(index_html, len(published_slugs))
    READER_OUT_DIR.mkdir(parents=True, exist_ok=True)
    (READER_OUT_DIR / "index.html").write_text(
        as_standalone_page(index_html),
        encoding="utf-8",
    )


def publish_next(publish_date: str | None = None) -> dict:
    init_pool()
    publish_date = publish_date or dt.datetime.now().strftime("%Y-%m-%d")
    pool = load_json(POOL_PATH, [])
    errors = load_json(ERROR_PATH, [])
    published = load_json(PUBLISHED_PATH, [])
    skipped: list[dict] = []

    selected = None
    selected_report = None
    for item in pool:
        report = audit(item)
        write_json(AUDIT_DIR / f"{item['slug']}.json", report)
        if report["status"] == "ok":
            selected = item
            selected_report = report
            break
        item_with_error = {**item, "audit": report, "failed_at": publish_date}
        errors.append(item_with_error)
        skipped.append(item)

    if not selected:
        write_json(POOL_PATH, [])
        write_json(ERROR_PATH, errors)
        render_static_index(published)
        return {"published": None, "skipped_errors": skipped}

    copy_static_paper(selected)
    copy_static_images(selected)

    remaining = [item for item in pool if item["slug"] not in {selected["slug"], *[x["slug"] for x in skipped]}]
    published.append(
        {
            **selected,
            "published_at": publish_date,
            "path": f"source/papers-reader/papers/{selected['slug']}.html",
            "audit": selected_report,
        }
    )
    render_static_index(published)
    write_json(POOL_PATH, remaining)
    write_json(ERROR_PATH, errors)
    write_json(PUBLISHED_PATH, published)
    return {"published": selected, "path": f"/papers-reader/papers/{selected['slug']}.html", "skipped_errors": skipped}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--init", action="store_true", help="initialize paper queue only")
    parser.add_argument("--force-init", action="store_true", help="rebuild pool from source index")
    parser.add_argument("--date", help="publish date, YYYY-MM-DD")
    args = parser.parse_args()

    if args.init or args.force_init:
        init_pool(force=args.force_init)
        print(f"pool size: {len(load_json(POOL_PATH, []))}")
        return

    result = publish_next(args.date)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
