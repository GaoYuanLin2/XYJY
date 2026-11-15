"""需求 2、3、4：发布（含图片）、分类与成色筛选、搜索、详情、分页。"""
import os
import re

from app.db import get_db
from tests.helpers import add_item, add_user, item_form, login, png_bytes


def test_publish_saves_pending_item(client, app):
    add_user(app, "stu1")
    login(client)
    response = client.post("/items/new", data=item_form(), follow_redirects=True)
    assert "发布成功".encode("utf-8") in response.data

    with app.app_context():
        row = get_db().execute("SELECT * FROM item").fetchone()
    assert row["status"] == "pending"
    assert row["price"] == 18.5
    assert row["category"] == "生活用品"


def test_published_item_hidden_from_index(client, app):
    add_user(app, "stu1")
    login(client)
    client.post("/items/new", data=item_form(), follow_redirects=True)
    response = client.get("/")
    assert "宿舍小台灯".encode("utf-8") not in response.data


def test_publish_with_image_makes_thumbnail(client, app):
    add_user(app, "stu1")
    login(client)
    data = item_form()
    data["image"] = (png_bytes(), "lamp.png")
    client.post("/items/new", data=data, content_type="multipart/form-data", follow_redirects=True)

    with app.app_context():
        row = get_db().execute("SELECT image, thumb FROM item").fetchone()
    assert row["image"].startswith("uploads/") and row["image"].endswith(".jpg")
    assert row["thumb"].endswith("_thumb.jpg")
    assert os.path.exists(os.path.join(app.config["UPLOAD_FOLDER"], os.path.basename(row["image"])))
    assert os.path.exists(os.path.join(app.config["UPLOAD_FOLDER"], os.path.basename(row["thumb"])))


def test_publish_rejects_non_positive_price(client, app):
    add_user(app, "stu1")
    login(client)
    for bad in ("0", "-5", "abc"):
        response = client.post("/items/new", data=item_form({"price": bad}),
                               follow_redirects=True)
        assert "价格".encode("utf-8") in response.data
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM item").fetchone()[0] == 0


def test_publish_rejects_unsupported_file(client, app):
    add_user(app, "stu1")
    login(client)
    data = item_form()
    data["image"] = (png_bytes(), "note.txt")
    response = client.post("/items/new", data=data, content_type="multipart/form-data",
                           follow_redirects=True)
    assert "只支持".encode("utf-8") in response.data


def test_publish_rejects_too_short_title(client, app):
    add_user(app, "stu1")
    login(client)
    response = client.post("/items/new", data=item_form({"title": "灯"}), follow_redirects=True)
    assert "标题".encode("utf-8") in response.data


def test_index_only_shows_approved(client, app):
    seller = add_user(app, "stu1")
    add_item(app, seller, status="approved", title="在售的教材")
    add_item(app, seller, status="pending", title="待审核的教材")
    add_item(app, seller, status="offline", title="已下架的教材")

    response = client.get("/")
    assert "在售的教材".encode("utf-8") in response.data
    assert "待审核的教材".encode("utf-8") not in response.data
    assert "已下架的教材".encode("utf-8") not in response.data


def test_category_and_condition_filter(client, app):
    seller = add_user(app, "stu1")
    add_item(app, seller, title="电子书", category="电子数码", condition="全新")
    add_item(app, seller, title="旧教材", category="图书教材", condition="明显使用")

    response = client.get("/?category=电子数码")
    assert "电子书".encode("utf-8") in response.data
    assert "旧教材".encode("utf-8") not in response.data

    response = client.get("/?condition=明显使用")
    assert "旧教材".encode("utf-8") in response.data
    assert "电子书".encode("utf-8") not in response.data

    response = client.get("/?category=图书教材&condition=明显使用")
    assert "旧教材".encode("utf-8") in response.data


def test_keyword_search_hits_title_and_description(client, app):
    seller = add_user(app, "stu1")
    add_item(app, seller, title="罗技鼠标", description="静音按键，无线")
    add_item(app, seller, title="宿舍台灯", description="USB 供电，三档亮度")

    response = client.get("/?q=鼠标")
    assert "罗技鼠标".encode("utf-8") in response.data
    assert "宿舍台灯".encode("utf-8") not in response.data

    response = client.get("/?q=三档")
    assert "宿舍台灯".encode("utf-8") in response.data
    assert "罗技鼠标".encode("utf-8") not in response.data


def test_price_sort(client, app):
    seller = add_user(app, "stu1")
    add_item(app, seller, title="贵的", price=99.0)
    add_item(app, seller, title="便宜的", price=9.5)

    response = client.get("/?sort=price_asc")
    assert response.data.index("便宜的".encode("utf-8")) < response.data.index("贵的".encode("utf-8"))

    response = client.get("/?sort=price_desc")
    assert response.data.index("贵的".encode("utf-8")) < response.data.index("便宜的".encode("utf-8"))


def test_cursor_pagination_has_no_duplicates(client, app):
    seller = add_user(app, "stu1")
    for index in range(8):
        add_item(app, seller, title="商品%02d 号" % index, price=10.0 + index)

    seen, cursor, guard = [], "", 0
    while guard < 10:
        guard += 1
        url = "/" if not cursor else "/?cursor=%s" % cursor
        text = client.get(url).data.decode("utf-8")
        seen.extend(re.findall(r"商品(\d{2}) 号", text))
        match = re.search(r"cursor=([A-Za-z0-9_\-]+)", text)
        if not match:
            break
        cursor = match.group(1)

    assert len(seen) == 8, "翻页总数不对：%r" % seen
    assert len(set(seen)) == 8, "翻页出现重复商品：%r" % seen


def test_detail_hidden_for_pending_item(client, app):
    seller = add_user(app, "stu1")
    item_id = add_item(app, seller, status="pending", title="待审核商品")
    response = client.get("/items/%d" % item_id)
    assert response.status_code == 404


def test_detail_visible_to_owner(client, app):
    seller = add_user(app, "stu1")
    item_id = add_item(app, seller, status="pending", title="待审核商品")
    login(client)
    response = client.get("/items/%d" % item_id)
    assert response.status_code == 200
    assert "待审核".encode("utf-8") in response.data


def test_edit_requires_owner(client, app):
    owner = add_user(app, "owner")
    add_user(app, "other")
    item_id = add_item(app, owner, title="别人的商品")
    login(client, "other")
    response = client.get("/items/%d/edit" % item_id)
    assert response.status_code == 404


def test_edit_resets_status_to_pending(client, app):
    owner = add_user(app, "owner")
    item_id = add_item(app, owner, status="approved", title="在售商品")
    login(client, "owner")
    response = client.post("/items/%d/edit" % item_id, data=item_form({"title": "改过的商品"}),
                           follow_redirects=True)
    assert "重新审核".encode("utf-8") in response.data
    with app.app_context():
        row = get_db().execute("SELECT title, status FROM item WHERE id = ?", (item_id,)).fetchone()
    assert row["title"] == "改过的商品"
    assert row["status"] == "pending"


def test_offline_by_owner_hides_item(client, app):
    owner = add_user(app, "owner")
    item_id = add_item(app, owner, status="approved", title="要下架的商品")
    login(client, "owner")
    response = client.post("/items/%d/offline" % item_id, follow_redirects=True)
    assert "已下架".encode("utf-8") in response.data
    with app.app_context():
        status = get_db().execute("SELECT status FROM item WHERE id = ?", (item_id,)).fetchone()[0]
    assert status == "offline"
    assert "要下架的商品".encode("utf-8") not in client.get("/").data
