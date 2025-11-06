# -*- coding: utf-8 -*-
"""
Thndr-report-temsah | Repo Audit
- يحصي الملفات حسب الامتداد والمجلد
- يحدد أكبر الملفات حجماً
- يلتقط مؤشرات أسرار شائعة (tokens, keys)
- يبحث عن متطلبات المشروع (requirements, pyproject, workflows, html templates)
- يخرج تقرير CSV + HTML داخل reports/
"""
import os, re, json, html, pathlib
from collections import Counter, defaultdict
from datetime import datetime

ROOT = pathlib.Path(".").resolve()
REPORTS = ROOT / "reports"
REPORTS.mkdir(parents=True, exist_ok=True)

EXT_SKIP = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".pdf", ".zip", ".rar"}
DIR_SKIP = {".git", ".github", "venv", ".venv", "node_modules", "__pycache__", "dist", "build", ".mypy_cache"}

SECRET_PATTERNS = {
    "generic_token": re.compile(r"(?:token|api[_-]?key|secret|bearer)\s*[:=]\s*['\"][A-Za-z0-9_\-\.]{12,}['\"]", re.I),
    "aws_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "gh_pat": re.compile(r"ghp_[A-Za-z0-9]{36,}"),
    "jwt": re.compile(r"eyJ[a-zA-Z0-9_\-]+?\.[a-zA-Z0-9_\-]+?\.[a-zA-Z0-9_\-]+"),
}

META_FILES = [
    "requirements.txt", "pyproject.toml", "Pipfile", "environment.yml",
    "package.json", "package-lock.json",
    "Dockerfile", "docker-compose.yml",
]

def walk_files():
    for root, dirs, files in os.walk(ROOT):
        # استثناء مجلدات
        dirs[:] = [d for d in dirs if d not in DIR_SKIP and not d.startswith(".pytest_cache")]
        for f in files:
            p = pathlib.Path(root) / f
            yield p

def sniff_secrets(path: pathlib.Path, max_bytes=200_000):
    try:
        if path.suffix.lower() in EXT_SKIP: return []
        if path.stat().st_size > max_bytes: return []
        txt = path.read_text(errors="ignore")
    except Exception:
        return []
    hits = []
    for name, rx in SECRET_PATTERNS.items():
        for m in rx.finditer(txt):
            frag = m.group(0)
            hits.append({"type": name, "match": frag[:60] + ("…" if len(frag)>60 else ""), "file": str(path)})
    return hits

def main():
    files = []
    ext_counter = Counter()
    dir_counter = Counter()
    largest = []
    secrets = []
    meta_found = []
    html_templates = []
    workflows = []

    for p in walk_files():
        rel = p.relative_to(ROOT)
        if rel.parts and rel.parts[0] in DIR_SKIP: 
            continue
        size = p.stat().st_size
        ext = p.suffix.lower()
        files.append({"path": str(rel), "size": size, "ext": ext})
        if ext: ext_counter[ext] += 1
        if rel.parts:
            dir_counter[rel.parts[0]] += 1
        # قوائم خاصة
        if rel.name in META_FILES:
            meta_found.append(str(rel))
        if "/templates/" in ("/" + "/".join(rel.parts) + "/"):
            if ext in {".html", ".jinja", ".j2"}:
                html_templates.append(str(rel))
        if rel.parts and rel.parts[0] == ".github" and "workflows" in rel.parts:
            workflows.append(str(rel))
        # أكبر 20 ملف
        largest.append((size, str(rel)))
        # أسرار
        secrets.extend(sniff_secrets(p))

    largest = sorted(largest, reverse=True)[:20]

    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "total_files": len(files),
        "by_ext": ext_counter.most_common(),
        "by_top_dir": dir_counter.most_common(),
        "largest_files": largest,
        "meta_found": meta_found,
        "html_templates": html_templates,
        "workflows": workflows,
        "secrets_hits": secrets[:200],
    }

    # CSV مبسط
    csv_path = REPORTS / "repo_files.csv"
    with csv_path.open("w", encoding="utf-8") as f:
        f.write("path,size,ext\n")
        for x in sorted(files, key=lambda r: r["path"].lower()):
            f.write(f"{x['path']},{x['size']},{x['ext']}\n")

    # HTML تقرير
    html_path = REPORTS / "repo_audit.html"
    def trow(k, v):
        return f"<tr><td style='font-weight:600'>{html.escape(k)}</td><td><pre style='white-space:pre-wrap'>{html.escape(v)}</pre></td></tr>"

    rows = []
    rows.append(trow("Total files", str(summary["total_files"])))
    rows.append(trow("Meta files", "\n".join(summary["meta_found"]) or "—"))
    rows.append(trow("HTML templates", "\n".join(summary["html_templates"]) or "—"))
    rows.append(trow("Workflows", "\n".join(summary["workflows"]) or "—"))
    rows.append(trow("By extension", "\n".join([f"{k}: {v}" for k,v in summary["by_ext"]]) or "—"))
    rows.append(trow("Top-level dirs", "\n".join([f"{k}: {v}" for k,v in summary["by_top_dir"]]) or "—"))
    rows.append(trow("Largest files", "\n".join([f"{sz:,}  {p}" for sz,p in summary["largest_files"]]) or "—"))
    if summary["secrets_hits"]:
        rows.append(trow("Potential secrets (review!)", "\n".join([f"{h['type']}: {h['match']}  →  {h['file']}" for h in summary["secrets_hits"]])))
    else:
        rows.append(trow("Potential secrets (review!)", "No obvious hits"))

    html_doc = f"""
    <!doctype html><html lang="ar"><meta charset="utf-8">
    <title>Thndr-report-temsah | Repo Audit</title>
    <style>
      body{{font-family:system-ui,-apple-system,Segoe UI,Roboto;max-width:1100px;margin:32px auto;padding:0 16px}}
      h1{{font-size:24px;margin:0 0 16px}}
      table{{width:100%;border-collapse:collapse}}
      td{{border:1px solid #ddd;padding:8px;vertical-align:top}}
      .note{{background:#f6f8fa;padding:8px;border-radius:8px;margin:8px 0}}
    </style>
    <h1>تقرير فحص الريبو</h1>
    <div class="note">تاريخ الإنشاء: {html.escape(summary["generated_at"])}</div>
    <table>{''.join(rows)}</table>
    <p class="note">تم إنشاء هذا التقرير تلقائيًا. راجع تحذيرات الأسرار المحتملة قبل نشر الكود.</p>
    </html>
    """
    html_path.write_text(html_doc, encoding="utf-8")

    # JSON
    (REPORTS / "repo_audit.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[OK] Wrote: {html_path}")
    print(f"[OK] Wrote: {csv_path}")

if __name__ == "__main__":
    main()
