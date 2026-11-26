"""Builds the blog: blog/<slug>/index.html for every post in blog-src/posts, blog/index.html, and sitemap.xml.

Run from anywhere: python3 -I blog-src/build.py

Each post file starts with an HTML comment holding a JSON header (title, description, h1, lede, date, image,
image_alt, card, related, faq, cta), then the article body as HTML.

When Collagio is public on Google Play, set PLAY_URL below and run the build again: every post's download box
then links to the listing, tagged with the post it came from.
"""

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "blog-src" / "posts"
OUT = ROOT / "blog"
SITE = "https://collagioapp.com"

# Empty until the listing is public (it is closed testing only, so the link would show "not found").
PLAY_URL = ""

FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com" />\n'
    '  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />\n'
    '  <link href="https://fonts.googleapis.com/css2?family=Fredoka:wght@500;600&family=Plus+Jakarta+Sans:wght@400;600;700&display=swap" rel="stylesheet" />'
)

HEADER = """<header class="site-head">
  <div class="wrap-wide">
    <a class="brand" href="/"><img src="/img/logo-mark.webp" alt="" width="34" height="34" /><span>Collagio</span></a>
    <nav class="head-nav" aria-label="Main">
      <a href="/#features" class="hide-sm">Features</a>
      <a href="/blog/">Blog</a>
      <a href="{cta_href}" class="btn-small">Get the app</a>
    </nav>
  </div>
</header>"""

FOOTER = """<footer class="site-foot">
  <div class="wrap-wide">
    <span>&copy; 2026 Cyberlab Automation</span>
    <nav aria-label="Footer">
      <a href="/">Home</a>
      <a href="/blog/">Blog</a>
      <a href="/privacy.html">Privacy policy</a>
      <a href="/terms.html">Terms of service</a>
      <a href="mailto:cyberlab.automation@gmail.com">Contact</a>
    </nav>
  </div>
</footer>"""


def play_link(slug):
    if not PLAY_URL:
        return "/#download"
    ref = f"utm_source%3Dcollagioapp.com%26utm_medium%3Dblog%26utm_campaign%3D{slug}"
    return f"{PLAY_URL}&referrer={ref}"


def cta_box(post):
    head = post.get("cta", {}).get("h", "Make it with Collagio")
    text = post.get("cta", {}).get(
        "p", "Collages and seamless Instagram carousels on your Android phone. Free to use, no account, and your photos stay on the phone."
    )
    if PLAY_URL:
        button = f'<a class="btn" href="{html.escape(play_link(post["slug"]))}">Get it on Google Play</a>'
        small = "Free on Google Play. Needs Android 8.0 or newer."
    else:
        button = '<a class="btn" href="/#download">See Collagio</a>'
        small = "Coming soon to Google Play. Needs Android 8.0 or newer."
    return f"""<aside class="cta" aria-label="Get Collagio">
  <img src="/img/logo-mark.webp" alt="" width="64" height="64" />
  <div>
    <h2>{html.escape(head)}</h2>
    <p>{html.escape(text)}</p>
    {button}
    <span class="small">{small}</span>
  </div>
</aside>"""


def read_post(path):
    raw = path.read_text(encoding="utf-8")
    m = re.match(r"\s*<!--(.*?)-->\s*(.*)", raw, re.S)
    if not m:
        raise SystemExit(f"{path.name}: no JSON header")
    meta = json.loads(m.group(1))
    meta["slug"] = path.stem
    meta["body"] = m.group(2).strip()
    for key in ("title", "description", "h1", "lede", "date", "image", "image_alt", "card"):
        if key not in meta:
            raise SystemExit(f"{path.name}: missing {key}")
    if len(meta["title"]) > 65:
        print(f"warning: {path.name} title is {len(meta['title'])} characters")
    if not 110 <= len(meta["description"]) <= 165:
        print(f"warning: {path.name} description is {len(meta['description'])} characters")
    return meta


def nice_date(iso):
    months = "January February March April May June July August September October November December".split()
    y, mo, d = iso.split("-")
    return f"{months[int(mo) - 1]} {int(d)}, {y}"


def faq_html(faq):
    if not faq:
        return ""
    items = "\n".join(f"<h3>{html.escape(q)}</h3>\n<p>{html.escape(a)}</p>" for q, a in faq)
    return f"<h2>Questions people ask</h2>\n{items}"


def schema(post):
    url = f"{SITE}/blog/{post['slug']}/"
    graph = [
        {
            "@type": "BlogPosting",
            "headline": post["h1"],
            "description": post["description"],
            "datePublished": post["date"],
            "dateModified": post.get("updated", post["date"]),
            "image": SITE + post["image"],
            "url": url,
            "mainEntityOfPage": url,
            "author": {"@type": "Organization", "name": "Collagio", "url": SITE + "/"},
            "publisher": {
                "@type": "Organization",
                "name": "Cyberlab Automation",
                "logo": {"@type": "ImageObject", "url": SITE + "/apple-touch-icon.png"},
            },
        },
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
                {"@type": "ListItem", "position": 2, "name": "Blog", "item": SITE + "/blog/"},
                {"@type": "ListItem", "position": 3, "name": post["h1"], "item": url},
            ],
        },
    ]
    if post.get("faq"):
        graph.append(
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
                    for q, a in post["faq"]
                ],
            }
        )
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, indent=2, ensure_ascii=False)


def card(post):
    return f"""<a class="card" href="/blog/{post['slug']}/">
  <img src="{post['image']}" alt="" loading="lazy" width="1014" height="687" />
  <div><h3>{html.escape(post['h1'])}</h3><p>{html.escape(post['card'])}</p></div>
</a>"""


def head(title, description, url, image, kind):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{html.escape(title)}</title>
  <meta name="description" content="{html.escape(description)}" />
  <link rel="canonical" href="{url}" />
  <meta name="theme-color" content="#ffffff" />
  <meta property="og:type" content="{kind}" />
  <meta property="og:site_name" content="Collagio" />
  <meta property="og:title" content="{html.escape(title)}" />
  <meta property="og:description" content="{html.escape(description)}" />
  <meta property="og:url" content="{url}" />
  <meta property="og:image" content="{image}" />
  <meta name="twitter:card" content="summary_large_image" />
  <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png" />
  <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
  {FONTS}
  <link rel="stylesheet" href="/blog/blog.css" />"""


def build_post(post, by_slug):
    url = f"{SITE}/blog/{post['slug']}/"
    related = [by_slug[s] for s in post.get("related", []) if s in by_slug]
    related_html = ""
    if related:
        related_html = (
            '<section class="related" aria-label="More guides">\n<h2>Keep reading</h2>\n<div class="cards">\n'
            + "\n".join(card(r) for r in related)
            + "\n</div>\n</section>"
        )
    page = f"""{head(post['title'], post['description'], url, SITE + post['image'], 'article')}
  <script type="application/ld+json">
{schema(post)}
  </script>
</head>
<body>
{HEADER.format(cta_href=play_link(post['slug']))}
<main class="wrap">
  <nav class="crumbs" aria-label="Breadcrumb"><a href="/">Home</a> / <a href="/blog/">Blog</a></nav>
  <header class="post-head">
    <h1>{html.escape(post['h1'])}</h1>
    <p class="lede">{html.escape(post['lede'])}</p>
    <p class="meta">By the Collagio team &middot; <time datetime="{post['date']}">{nice_date(post['date'])}</time></p>
  </header>
  <div class="hero-img"><img src="{post['image']}" alt="{html.escape(post['image_alt'])}" width="1014" height="687" /></div>
  <article>
{post['body']}
{faq_html(post.get('faq'))}
  </article>
{cta_box(post)}
{related_html}
</main>
{FOOTER}
</body>
</html>
"""
    out = OUT / post["slug"] / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")


def build_index(posts):
    url = f"{SITE}/blog/"
    title = "Collagio Blog: Collage and Instagram Carousel Guides"
    description = "Guides to photo collages, seamless Instagram carousels, post sizes and photo edits on Android, from the people who make Collagio."
    cards = "\n".join(card(p) for p in posts)
    page = f"""{head(title, description, url, SITE + '/og-image.jpg', 'website')}
</head>
<body>
{HEADER.format(cta_href=play_link('blog-index'))}
<main class="wrap-wide">
  <header class="blog-head">
    <h1>Collage and carousel guides</h1>
    <p>How to make collages, seamless Instagram carousels and cleaner photos on an Android phone, with the sizes and steps that matter.</p>
  </header>
  <div class="cards">
{cards}
  </div>
</main>
{FOOTER}
</body>
</html>
"""
    (OUT / "index.html").write_text(page, encoding="utf-8")


def build_sitemap(posts):
    rows = [
        (f"{SITE}/", "2026-11-25"),
        (f"{SITE}/blog/", max(p.get("updated", p["date"]) for p in posts)),
    ]
    rows += [(f"{SITE}/blog/{p['slug']}/", p.get("updated", p["date"])) for p in posts]
    rows += [(f"{SITE}/privacy.html", "2026-11-13"), (f"{SITE}/terms.html", "2026-11-12")]
    body = "\n".join(f"  <url><loc>{u}</loc><lastmod>{d}</lastmod></url>" for u, d in rows)
    (ROOT / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{body}\n</urlset>\n',
        encoding="utf-8",
    )


def main():
    posts = [read_post(p) for p in sorted(SRC.glob("*.html"))]
    posts.sort(key=lambda p: (p.get("order", 99), p["slug"]))
    by_slug = {p["slug"]: p for p in posts}
    for p in posts:
        for s in p.get("related", []):
            if s not in by_slug:
                raise SystemExit(f"{p['slug']}: related post {s} does not exist")
        build_post(p, by_slug)
    build_index(posts)
    build_sitemap(posts)
    print(f"built {len(posts)} posts, the blog index and sitemap.xml")


if __name__ == "__main__":
    main()
