-- 校园二手交易平台 数据库结构（SQLite）
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS user (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE,
    nickname      TEXT    NOT NULL,
    password_hash TEXT    NOT NULL,
    role          TEXT    NOT NULL DEFAULT 'user',   -- user / admin
    created_at    TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS item (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,
    description TEXT    NOT NULL DEFAULT '',
    price       REAL    NOT NULL CHECK (price > 0),
    category    TEXT    NOT NULL,
    condition   TEXT    NOT NULL,
    image       TEXT,                                 -- 原图（相对 static）
    thumb       TEXT,                                 -- 缩略图，列表页只加载它
    status      TEXT    NOT NULL DEFAULT 'pending',   -- pending/approved/rejected/offline/sold
    seller_id   INTEGER NOT NULL REFERENCES user (id),
    review_note TEXT,
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_item_status_time ON item (status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_item_category ON item (category, condition);
CREATE INDEX IF NOT EXISTS idx_item_title ON item (title);

CREATE TABLE IF NOT EXISTS favorite (
    user_id    INTEGER NOT NULL REFERENCES user (id),
    item_id    INTEGER NOT NULL REFERENCES item (id),
    created_at TEXT    NOT NULL,
    PRIMARY KEY (user_id, item_id)
);

CREATE TABLE IF NOT EXISTS message (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id    INTEGER NOT NULL REFERENCES item (id),
    user_id    INTEGER NOT NULL REFERENCES user (id),
    parent_id  INTEGER REFERENCES message (id),
    content    TEXT    NOT NULL,
    created_at TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_message_item ON message (item_id, created_at);

CREATE TABLE IF NOT EXISTS trade_order (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id    INTEGER NOT NULL REFERENCES item (id),
    buyer_id   INTEGER NOT NULL REFERENCES user (id),
    seller_id  INTEGER NOT NULL REFERENCES user (id),
    status     TEXT    NOT NULL DEFAULT 'pending',   -- pending/confirmed/completed/cancelled
    created_at TEXT    NOT NULL,
    updated_at TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_order_item ON trade_order (item_id, status);
CREATE INDEX IF NOT EXISTS idx_order_buyer ON trade_order (buyer_id, status);
CREATE INDEX IF NOT EXISTS idx_order_seller ON trade_order (seller_id, status);