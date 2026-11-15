"""用 Playwright 驱动真实页面，截取演示与验收要用的 6 张图。"""
import pathlib
import sys

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5055"
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "screens"
OUT.mkdir(parents=True, exist_ok=True)

PAGES = [
    ("01-首页列表", "/"),
    ("02-商品详情", "/items/1"),
    ("03-发布商品", "/items/new"),
    ("04-我的收藏", "/favorites"),
    ("05-我的订单", "/orders"),
    ("06-后台审核", "/admin"),
]


def login(page, username, password):
    page.goto(BASE + "/login")
    page.fill("input[name=username]", username)
    page.fill("input[name=password]", password)
    page.click("button[type=submit]")
    page.wait_for_load_state("networkidle")


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 900}, device_scale_factor=1)
    login(page, "gaoyuanlin", "123456")
    for name, path in PAGES:
        if name.startswith("06"):
            page.goto(BASE + "/logout")
            login(page, "admin", "admin123456")
        resp = page.goto(BASE + path)
        page.wait_for_load_state("networkidle")
        status = resp.status if resp else "?"
        target = OUT / (name + ".png")
        page.screenshot(path=str(target), full_page=True)
        print(name, path, status, target.stat().st_size)
    browser.close()
print("done", file=sys.stderr)