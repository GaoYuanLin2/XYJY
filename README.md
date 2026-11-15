# 校园二手交易平台（XYJY · 先跑再说队）

信息系统项目管理实训项目：面向在校学生的校园二手交易平台。学生发布闲置 → 管理员审核 → 同学浏览搜索 → 收藏留言 → 下单交易，全流程留痕。

## 功能清单（8 条需求）

| 编号 | 需求 | 版本 | 状态 |
| --- | --- | --- | --- |
| 1 | 注册、登录、退出与访问控制 | v1.0 | 已完成 |
| 2 | 发布商品（标题/价格/分类/成色/描述/传图，图片自动生成缩略图） | v1.0 | 已完成 |
| 3 | 分类 + 成色两维筛选浏览、商品详情 | v1.0 | 已完成 |
| 4 | 关键词搜索（标题/描述/分类/成色）、价格排序、游标分页 | v1.0 | 已完成 |
| 5 | 收藏 / 取消收藏、我的收藏 | v2.0 | 已完成 |
| 6 | 留言与卖家回复 | v2.0 | 已完成 |
| 7 | 订单状态流转（待确认 → 已确认 → 已完成 / 已取消） | v2.0 | 已完成 |
| 8 | 后台审核（通过 / 驳回并填写原因）、下架 | v2.0 | 已完成 |

## 技术栈

- Python 3.11 + Flask 3（服务端渲染，Jinja2 模板）
- SQLite（`app/schema.sql` 建表，索引覆盖状态+时间、分类+成色、标题）
- Pillow 处理图片：原图最长边压到 1600px，另生成 480px 缩略图，列表页只加载缩略图
- pytest 单元与接口测试，flake8 代码检查，GitHub Actions 持续集成

## 目录结构

```
XYJY/
├── app/
│   ├── __init__.py      应用工厂
│   ├── db.py            SQLite 连接与 init-db 命令
│   ├── schema.sql       建表语句与索引
│   ├── auth.py          需求 1：注册登录、登录/管理员校验
│   ├── items.py         需求 2/3/4：发布、筛选、搜索、分页、下架
│   ├── social.py        需求 5/6：收藏、留言与回复
│   ├── orders.py        需求 7：订单状态机
│   ├── admin.py         需求 8：后台审核与下架
│   ├── seed.py          演示数据命令
│   ├── templates/       Jinja2 模板
│   └── static/          样式与上传图片
├── tests/               54 条 pytest 用例
├── docs/                需求清单、数据库设计、测试说明
├── .github/workflows/   CI（flake8 + pytest）
├── run.py               开发入口
└── requirements.txt
```

## 本地运行

```bash
python -m venv .venv
.venv\Scripts\activate           # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
flask --app run init-db          # 建表
flask --app run seed-demo        # 可选：写入演示数据
python run.py                    # 打开 http://127.0.0.1:5000
```

演示账号：管理员 `admin / admin123456`，普通用户 `gaoyuanlin / 123456`、`lisi / 123456`、`wangwu / 123456`。

## 测试与检查

```bash
python -m pytest -q              # 54 条用例
flake8 app tests run.py          # 代码检查
```

## 版本

- `v1.0`：需求 1—4，注册登录、发布商品、分类成色筛选、搜索排序分页
- `v2.0`：需求 5—8，收藏、留言、订单状态机、后台审核；并修复 v1 遗留的价格校验、分页重复、图片未压缩三个问题

## 说明

本项目为教学实训项目，不含在线支付与物流；交易在校园内当面完成，平台只负责信息撮合与状态记录。