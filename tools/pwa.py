#!/usr/bin/env python3
"""تثبيت المدونة كتطبيق (PWA): الأيقونات و manifest.webmanifest و sw.js ووسوم الصفحات.
التشغيل: python3 tools/pwa.py  (من جذر المستودع)
يُعاد تشغيله عند تغيّر الاسم أو الهوية أو الشعار. آمن للتكرار (idempotent).
"""
import json, re, pathlib, hashlib

ROOT = pathlib.Path(__file__).resolve().parent.parent

# ===== إعدادات المدونة (تُعدّل هنا عند تغيير الاسم أو الهوية) =====
APP_NAME   = "مدونة خالد الواصل"
SHORT_NAME = "خالد الواصل"          # ١٢ حرفاً أو أقل
DESCRIPTION = "كتب قرأها، وكلمات استوقفته، وخواطر كتبها الأستاذ خالد الواصل."
PRIMARY = "#17365D"; ACCENT = "#D9B978"; BG = "#F7F3E8"; MUTED = "#9FB0C6"; DARK_ACCENT = "#7D6024"
PAGES = ["index.html"]
CATEGORIES = ["books", "education", "lifestyle"]

# الشعار: كتاب مفتوح وقلم (نفس شعار favicon.svg بدون الخلفية)، محصور في مربع 40×40
LOGO = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="12.5 8 40 40">
<path d="M32 22c-5-4-11-5-18-4v26c7-1 13 0 18 4 5-4 11-5 18-4V18c-7-1-13 0-18 4z" fill="{BG}"/>
<path d="M32 22v26" stroke="{PRIMARY}" stroke-width="2.4"/>
<path d="M18 25c4-.3 7 .4 10 2M18 31c4-.3 7 .4 10 2M18 37c4-.3 7 .4 10 2" stroke="{MUTED}" stroke-width="1.8" fill="none" stroke-linecap="round"/>
<path d="M48 8 36 30l-1.5 5.5L39 31.5 51 10z" fill="{ACCENT}"/>
<path d="M34.5 35.5 36 30l3 1.5z" fill="{DARK_ACCENT}"/>
</svg>'''

ICONS = [  # (الملف، المقاس، نسبة الشعار)
    ("assets/icon-192.png", 192, .70),
    ("assets/icon-512.png", 512, .70),
    ("assets/icon-maskable-512.png", 512, .54),
    ("assets/apple-touch-icon.png", 180, .66),
    ("assets/favicon-32.png", 32, .86),
]

def write_if_changed(path, data):
    path = ROOT / path
    data = data.encode() if isinstance(data, str) else data
    if path.exists() and path.read_bytes() == data:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    print("كُتب:", path.relative_to(ROOT))
    return True

def icons():
    stamp = ROOT / "assets/.icons-hash"
    h = hashlib.md5((LOGO + PRIMARY + repr(ICONS)).encode()).hexdigest()
    if stamp.exists() and stamp.read_text() == h and all((ROOT / f).exists() for f, _, _ in ICONS):
        return
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        for f, s, r in ICONS:
            pg = b.new_page(viewport={"width": s, "height": s})
            d = round(s * r)
            pg.set_content(f'<body style="margin:0;width:{s}px;height:{s}px;background:{PRIMARY};display:grid;place-items:center">'
                           + LOGO.replace("<svg ", f'<svg width="{d}" height="{d}" ') + '</body>')
            write_if_changed(f, pg.screenshot())
        b.close()
    write_if_changed("assets/.icons-hash", h)
    # أيقونة SVG للتبويب بنفس الشعار
    write_if_changed("assets/favicon.svg", f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="{PRIMARY}"/>'
                     + re.sub(r'^<svg[^>]*>|</svg>$', '', LOGO.strip()) + '</svg>\n')

def manifest():
    m = {
        "id": "./", "name": APP_NAME, "short_name": SHORT_NAME, "description": DESCRIPTION,
        "lang": "ar", "dir": "rtl", "start_url": "./", "scope": "./",
        "display": "standalone", "orientation": "any",
        "theme_color": PRIMARY, "background_color": PRIMARY, "categories": CATEGORIES,
        "icons": [
            {"src": "assets/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": "assets/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": "assets/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }
    write_if_changed("manifest.webmanifest", json.dumps(m, ensure_ascii=False, indent=2) + "\n")

SW = '''// عامل خدمة خفيف للتثبيت كتطبيق (يُولَّد من tools/pwa.py)
// الصفحات: من الشبكة أولاً دائماً (فلا تظهر نسخة قديمة)، ومن النسخة المحفوظة فقط عند انقطاع الاتصال.
// بقية الملفات (الصور والخطوط والبيانات) لا يتدخّل فيها، فتبقى مع ذاكرة المتصفح العادية.
const CACHE = "lib-pages-v1";
self.addEventListener("install", (e) => { self.skipWaiting(); });
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k.startsWith("lib-pages-") && k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", (e) => {
  const r = e.request;
  if (r.method !== "GET" || r.mode !== "navigate") return;
  e.respondWith(fetch(r).then((res) => {
    if (res && res.ok) { const c = res.clone(); const u = new URL(r.url); u.search = ""; caches.open(CACHE).then((ca) => ca.put(u.href, c)); }
    return res;
  }).catch(() => caches.match(r, { ignoreSearch: true }).then((m) => m || caches.match(new URL("./", self.registration.scope).href))));
});
'''

def tags(prefix=""):
    return f'''<!-- PWA:START -->
<link rel="manifest" href="{prefix}manifest.webmanifest">
<link rel="icon" type="image/svg+xml" href="{prefix}assets/favicon.svg">
<link rel="icon" type="image/png" sizes="32x32" href="{prefix}assets/favicon-32.png">
<link rel="icon" type="image/png" sizes="192x192" href="{prefix}assets/icon-192.png">
<link rel="apple-touch-icon" sizes="180x180" href="{prefix}assets/apple-touch-icon.png">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="{SHORT_NAME}">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<script>if("serviceWorker" in navigator)addEventListener("load",function(){{navigator.serviceWorker.register("{prefix}sw.js").catch(function(){{}});}});</script>
<!-- PWA:END -->'''

def pages():
    for name in PAGES:
        p = ROOT / name
        if not p.exists():
            continue
        s = p.read_text(encoding="utf-8")
        s = re.sub(r'\n?<!-- PWA:START -->.*?<!-- PWA:END -->', '', s, flags=re.S)
        # حذف أسطر الأيقونات القديمة خارج القسم
        s = re.sub(r'\n?[ \t]*<link rel="(?:icon|apple-touch-icon|shortcut icon)"[^>]*>', '', s)
        s = s.replace("</head>", tags() + "\n</head>", 1)
        write_if_changed(name, s)
    # ملفات الأيقونات القديمة في الجذر
    for old in ["favicon.svg", "favicon-32.png", "apple-touch-icon.png"]:
        if (ROOT / old).exists():
            (ROOT / old).unlink(); print("حُذف:", old)

if __name__ == "__main__":
    icons(); manifest(); write_if_changed("sw.js", SW); pages()
    print("تم.")
