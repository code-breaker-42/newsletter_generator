import argparse
import json
import re
from pathlib import Path


import requests
from bs4 import BeautifulSoup


def fetch(url):
# Fetch page HTML with basic headers; 15-second timeout
    headers = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    return r.text


def first_paragraph_text(soup):
    p = soup.find("p")
    if not p:
        return ""
    # strip tags
    import re as _re
    return _re.sub(r"<[^>]+>", "", p.decode()).strip()


def parse_article(html, url):
# Parse OpenGraph/JSON-LD; fall back to title/first paragraph
    soup = BeautifulSoup(html, "html.parser")


    def meta_property(prop):
        tag = soup.find("meta", property=prop)
        if tag and tag.has_attr("content"):
            return (tag.get("content") or "").strip()
        return ""


    def meta_name(name):
        tag = soup.find("meta", attrs={"name": name})
        if tag and tag.has_attr("content"):
            return (tag.get("content") or "").strip()
        return ""


    title = meta_property("og:title") or (soup.title.string.strip() if soup.title else "")
    desc = meta_property("og:description") or meta_name("description") or ""
    img = meta_property("og:image") or ""


    # Try to find JSON-LD Article / NewsArticle
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string)
        except Exception:
            continue
        candidates = data if isinstance(data, list) else [data]
        for d in candidates:
            t = d.get("@type")
            if not t:
                continue
        t_list = t if isinstance(t, list) else [t]
        if any(x in ("Article", "NewsArticle", "BlogPosting") for x in t_list):
            title = title or d.get("headline", "")
            desc = desc or d.get("description", "")
            image_field = d.get("image")
            if isinstance(image_field, dict):
                img = img or image_field.get("url", "")
            elif isinstance(image_field, list) and image_field:
                img = img or image_field[0]
            elif isinstance(image_field, str):
                img = img or image_field
            break

    first_p = first_paragraph_text(soup)


    # Final clean-ups
    title = (title or "").strip()
    desc = (desc or "").strip()
    first_p = (first_p or "").strip()

    return {"url": url, "title": title, "desc": desc, "img": img, "first_p": first_p}

def summarize_blurb(item, max_len=220):
    # Cheap non-LLM blurb: prefer description; else first paragraph; clamp length
    import re as _re
    text = item.get("desc") or item.get("first_p") or ""
    text = _re.sub(r"\s+", " ", text).strip()
    if len(text) > max_len:
        text = text[: max_len - 1].rstrip() + "…"
    return text

def pick_main_and_lists(items):
    # Pick main by longest blurb; others sorted after that
    def blen(x):
        return len((x.get("desc") or x.get("first_p") or ""))
    items_sorted = sorted(items, key=blen, reverse=True)
    main = items_sorted[0]
    others = items_sorted[1:]
    quick = others[:3]
    rec = items_sorted[1:4]
    return main, others, quick, rec


def render_html(template_path, ctx):
    tpl = Path(template_path).read_text(encoding="utf-8")
    out = tpl
    for k, v in ctx.items():
        out = out.replace("{{" + k + "}}", v or "")
    return out


def ensure_same_domain(urls):
    domains = [re.findall(r"^https?://([^/]+)", u, flags=re.I)[0] for u in urls]
    base = domains[0]
    if not all(d == base for d in domains):
        raise SystemExit("All URLs must be from the same domain. Found: " + ", ".join(sorted(set(domains))))
    return base

def main():
    ap = argparse.ArgumentParser(description="Build a newsletter (HTML) from 2–10 article URLs (same domain).")
    ap.add_argument("urls", nargs="*", help="Article URLs (same domain). If empty, reads from urls.txt")
    ap.add_argument("--template", default="newsletter_template.html", help="HTML template file")
    ap.add_argument("--out", default="newsletter_output.html", help="Output HTML file")
    args = ap.parse_args()


    urls = args.urls
    if not urls:
        url_file = Path("urls.txt")
        if url_file.exists():
            urls = [ln.strip() for ln in url_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if len(urls) < 2:
        raise SystemExit("Provide at least 2 URLs (same domain), either as CLI args or in urls.txt")

    base = ensure_same_domain(urls)

    items = []
    for u in urls:
        print("[fetch]", u)
        try:
            html = fetch(u)
            art = parse_article(html, u)
            art["blurb"] = summarize_blurb(art)
            items.append(art)
        except Exception as e:
            print(" ! skipped:", e)


    if not items:
        raise SystemExit("No articles could be fetched/parsed.")


    main_item, others, quick, rec = pick_main_and_lists(items)


    def g(lst, i, key):
        try:
            return lst[i].get(key, "") if i < len(lst) else ""
        except Exception:
            return ""
        
    ctx = {
        "NEWSLETTER_TITLE": "This Week on " + base,
        "NEWSLETTER_SUBTITLE": "",
        "MAIN_IMAGE_URL": main_item.get("img") or ("https://" + base + "/favicon.ico"),
        "MAIN_URL": main_item.get("url", ""),
        "MAIN_TITLE": main_item.get("title", ""),
        "MAIN_SUMMARY": main_item.get("blurb", ""),

        "S1_URL": g(others, 0, "url"),
        "S1_TITLE": g(others, 0, "title"),
        "S1_BLURB": g(others, 0, "blurb"),
        "S2_URL": g(others, 1, "url"),
        "S2_TITLE": g(others, 1, "title"),
        "S2_BLURB": g(others, 1, "blurb"),
        "S3_URL": g(others, 2, "url"),
        "S3_TITLE": g(others, 2, "title"),
        "S3_BLURB": g(others, 2, "blurb"),

        "Q1_URL": g(quick, 0, "url"),
        "Q1_TITLE": g(quick, 0, "title"),
        "Q2_URL": g(quick, 1, "url"),
        "Q2_TITLE": g(quick, 1, "title"),
        "Q3_URL": g(quick, 2, "url"),
        "Q3_TITLE": g(quick, 2, "title"),

        "R1_URL": g(rec, 0, "url"),
        "R1_TITLE": g(rec, 0, "title"),
        "R2_URL": g(rec, 1, "url"),
        "R2_TITLE": g(rec, 1, "title"),
        "R3_URL": g(rec, 2, "url"),
        "R3_TITLE": g(rec, 2, "title"),

        "BRAND_NAME": base,
        "YEAR": "2025",
        "ADDRESS_LINE": "—",
    }

    html = render_html(args.template, ctx)
    Path(args.out).write_text(html, encoding="utf-8")
    print("[done] Wrote", args.out)
    print("Open it in a browser; copy HTML into Gmail/MailerLite.")


if __name__ == "__main__":
    main()
    

    