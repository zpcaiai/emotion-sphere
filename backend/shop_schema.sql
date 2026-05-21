-- ============================================================
-- 虚拟商品 + 订单 + 微信支付 Schema
-- 情感星球 Emotion Sphere
-- ============================================================

-- ── 1. 商品分类 ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS shop_categories (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    name_en     VARCHAR(100) DEFAULT '',
    icon        VARCHAR(255) DEFAULT '',
    sort_order  INTEGER DEFAULT 0,
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_shop_categories_name ON shop_categories(name);
CREATE INDEX IF NOT EXISTS idx_shop_categories_sort ON shop_categories(sort_order);

-- ── 2. 虚拟商品表 ─────────────────────────────────────────────
-- 商品类型: subscription(订阅), credits(积分/星星币), feature_unlock(功能解锁),
--           theme(主题皮肤), report(深度分析报告), gift(礼品卡)
CREATE TABLE IF NOT EXISTS shop_products (
    id              SERIAL PRIMARY KEY,
    category_id     INTEGER REFERENCES shop_categories(id) ON DELETE SET NULL,
    sku             VARCHAR(100) NOT NULL UNIQUE,           -- 商品唯一编码
    name            VARCHAR(200) NOT NULL,
    name_en         VARCHAR(200) DEFAULT '',
    description     TEXT DEFAULT '',
    product_type    VARCHAR(50) NOT NULL DEFAULT 'credits', -- subscription/credits/feature_unlock/theme/report/gift
    price_fen       INTEGER NOT NULL CHECK (price_fen >= 0),-- 人民币分
    original_price_fen INTEGER DEFAULT 0,                  -- 划线价（分）
    credits_grant   INTEGER DEFAULT 0,                     -- 购买后赠送积分数量
    duration_days   INTEGER DEFAULT 0,                     -- 订阅/权益有效期（0=永久）
    feature_keys    TEXT[] DEFAULT '{}',                   -- 解锁功能的 key 列表
    metadata        JSONB DEFAULT '{}',                    -- 扩展字段（如封面图、详情图等）
    stock           INTEGER DEFAULT -1,                    -- -1=不限库存
    sold_count      INTEGER DEFAULT 0,
    is_active       BOOLEAN DEFAULT TRUE,
    sort_order      INTEGER DEFAULT 0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_shop_products_sku ON shop_products(sku);
CREATE INDEX IF NOT EXISTS idx_shop_products_type ON shop_products(product_type);
CREATE INDEX IF NOT EXISTS idx_shop_products_active ON shop_products(is_active, sort_order);
CREATE INDEX IF NOT EXISTS idx_shop_products_category ON shop_products(category_id);

-- ── 3. 订单主表 ───────────────────────────────────────────────
-- 状态机: pending_payment → paid → delivering → fulfilled
--          └──→ cancelled / refunding → refunded
--          └──→ payment_failed
CREATE TABLE IF NOT EXISTS shop_orders (
    id              BIGSERIAL PRIMARY KEY,
    order_no        VARCHAR(64) NOT NULL UNIQUE,            -- 业务订单号: ES{yyyyMMddHHmmss}{6位随机}
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    product_id      INTEGER NOT NULL REFERENCES shop_products(id) ON DELETE RESTRICT,
    product_sku     VARCHAR(100) NOT NULL,                  -- 下单时快照
    product_name    VARCHAR(200) NOT NULL,                  -- 下单时快照
    product_type    VARCHAR(50) NOT NULL,
    quantity        INTEGER NOT NULL DEFAULT 1 CHECK (quantity >= 1),
    unit_price_fen  INTEGER NOT NULL CHECK (unit_price_fen >= 0),
    total_price_fen INTEGER NOT NULL CHECK (total_price_fen >= 0),
    credits_grant   INTEGER DEFAULT 0,                     -- 本订单赠送积分数
    duration_days   INTEGER DEFAULT 0,
    feature_keys    TEXT[] DEFAULT '{}',

    -- 支付信息
    pay_channel     VARCHAR(30) DEFAULT 'wxpay',           -- wxpay / alipay / apple_iap
    pay_method      VARCHAR(30) DEFAULT '',                -- jsapi / miniprogram / native / h5
    wx_prepay_id    VARCHAR(255) DEFAULT '',               -- 微信预支付ID
    wx_transaction_id VARCHAR(64) DEFAULT '',              -- 微信支付交易号
    wx_out_trade_no  VARCHAR(64) DEFAULT '',               -- 传给微信的商户订单号（≈order_no）

    -- 状态
    status          VARCHAR(30) NOT NULL DEFAULT 'pending_payment',
    -- pending_payment / paid / delivering / fulfilled / cancelled / refunding / refunded / payment_failed

    -- 时间节点
    paid_at         TIMESTAMP,
    fulfilled_at    TIMESTAMP,
    cancelled_at    TIMESTAMP,
    expired_at      TIMESTAMP,                             -- 支付超期时间（下单+30min）
    refunded_at     TIMESTAMP,

    -- 退款
    refund_reason   TEXT DEFAULT '',
    refund_amount_fen INTEGER DEFAULT 0,
    wx_refund_id    VARCHAR(64) DEFAULT '',

    -- 来源标记
    client_ip       VARCHAR(45) DEFAULT '',
    platform        VARCHAR(20) DEFAULT 'web',             -- web / miniprogram / h5

    -- 元数据
    remark          TEXT DEFAULT '',
    extra           JSONB DEFAULT '{}',

    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_orders_user ON shop_orders(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_status ON shop_orders(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_order_no ON shop_orders(order_no);
CREATE INDEX IF NOT EXISTS idx_orders_wx_trade ON shop_orders(wx_transaction_id) WHERE wx_transaction_id != '';
CREATE INDEX IF NOT EXISTS idx_orders_created ON shop_orders(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_expired ON shop_orders(expired_at) WHERE status = 'pending_payment';

-- ── 4. 微信支付回调日志 ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS wxpay_notify_logs (
    id              BIGSERIAL PRIMARY KEY,
    order_no        VARCHAR(64) DEFAULT '',
    wx_transaction_id VARCHAR(64) DEFAULT '',
    event_type      VARCHAR(50) DEFAULT '',                -- TRANSACTION.SUCCESS / REFUND.SUCCESS 等
    raw_body        TEXT NOT NULL,                        -- 原始回调 JSON
    headers         JSONB DEFAULT '{}',                   -- 回调 HTTP 头（含签名）
    verified        BOOLEAN DEFAULT FALSE,                -- 签名是否验证通过
    processed       BOOLEAN DEFAULT FALSE,                -- 业务处理是否成功
    error_msg       TEXT DEFAULT '',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_wxpay_notify_order ON wxpay_notify_logs(order_no);
CREATE INDEX IF NOT EXISTS idx_wxpay_notify_tx ON wxpay_notify_logs(wx_transaction_id);
CREATE INDEX IF NOT EXISTS idx_wxpay_notify_created ON wxpay_notify_logs(created_at DESC);

-- ── 5. 用户权益/积分账户 ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_entitlements (
    id              BIGSERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    credits_balance INTEGER NOT NULL DEFAULT 0 CHECK (credits_balance >= 0),
    -- 已解锁功能 key 集合（JSONB 数组，便于查询）
    unlocked_features JSONB DEFAULT '[]',
    -- 订阅到期时间（NULL=无订阅）
    subscription_expires_at TIMESTAMP,
    subscription_plan VARCHAR(100) DEFAULT '',
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id)
);

CREATE INDEX IF NOT EXISTS idx_entitlements_user ON user_entitlements(user_id);

-- ── 6. 积分/权益流水账 ────────────────────────────────────────
-- event_type: purchase_grant / consume / refund_deduct / admin_adjust / expiry
CREATE TABLE IF NOT EXISTS credits_ledger (
    id              BIGSERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    order_id        BIGINT REFERENCES shop_orders(id) ON DELETE SET NULL,
    event_type      VARCHAR(50) NOT NULL,
    delta           INTEGER NOT NULL,                     -- 正=入账, 负=支出
    balance_after   INTEGER NOT NULL,
    note            TEXT DEFAULT '',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ledger_user ON credits_ledger(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ledger_order ON credits_ledger(order_id);

-- ── 7. 初始商品数据 ───────────────────────────────────────────

INSERT INTO shop_categories (name, name_en, icon, sort_order) VALUES
    ('星星币',    'Credits',      '⭐', 1),
    ('高级订阅',  'Subscription', '👑', 2),
    ('功能解锁',  'Features',     '🔓', 3),
    ('主题皮肤',  'Themes',       '🎨', 4),
    ('深度报告',  'Reports',      '📊', 5)
ON CONFLICT (name) DO NOTHING;

-- 星星币充值包
INSERT INTO shop_products (category_id, sku, name, description, product_type, price_fen, original_price_fen, credits_grant, sort_order) VALUES
    ((SELECT id FROM shop_categories WHERE name='星星币'), 'credits_30',  '30颗星星币',   '可用于解锁深度分析报告、主题皮肤等', 'credits', 300,    0,   30,  1),
    ((SELECT id FROM shop_categories WHERE name='星星币'), 'credits_98',  '98颗星星币',   '超值优惠包，赠送8颗', 'credits',         900,    980, 98,  2),
    ((SELECT id FROM shop_categories WHERE name='星星币'), 'credits_328', '328颗星星币',  '年度囤货大包，省40%', 'credits',        2800,   4920, 328, 3)
ON CONFLICT (sku) DO NOTHING;

-- 高级订阅
INSERT INTO shop_products (category_id, sku, name, description, product_type, price_fen, original_price_fen, duration_days, feature_keys, sort_order) VALUES
    ((SELECT id FROM shop_categories WHERE name='高级订阅'), 'sub_monthly',  '高级版月订阅',  '解锁全部高级功能，30天', 'subscription', 1800, 2800, 30,  ARRAY['psychology_deep','habit_analysis','formation_full','dss_full'], 1),
    ((SELECT id FROM shop_categories WHERE name='高级订阅'), 'sub_yearly',   '高级版年订阅',  '解锁全部高级功能，365天，省50%', 'subscription', 16800, 33600, 365, ARRAY['psychology_deep','habit_analysis','formation_full','dss_full'], 2),
    ((SELECT id FROM shop_categories WHERE name='高级订阅'), 'sub_lifetime', '高级版终身会员','一次解锁，终身使用', 'subscription', 49800, 99800, 36500, ARRAY['psychology_deep','habit_analysis','formation_full','dss_full'], 3)
ON CONFLICT (sku) DO NOTHING;

-- 功能解锁（永久单买）
INSERT INTO shop_products (category_id, sku, name, description, product_type, price_fen, original_price_fen, feature_keys, sort_order) VALUES
    ((SELECT id FROM shop_categories WHERE name='功能解锁'), 'unlock_psychology', '深度心理分析', '解锁 L0-L4 全层人格因果引擎', 'feature_unlock', 2800, 3800, ARRAY['psychology_deep'], 1),
    ((SELECT id FROM shop_categories WHERE name='功能解锁'), 'unlock_dss',        '决策支持系统', '解锁灵性决策支持全功能',       'feature_unlock', 1800, 2800, ARRAY['dss_full'],         2),
    ((SELECT id FROM shop_categories WHERE name='功能解锁'), 'unlock_formation',  '灵命成长追踪', '解锁灵命操练记录与成长报告',   'feature_unlock', 1800, 2400, ARRAY['formation_full'],    3)
ON CONFLICT (sku) DO NOTHING;

-- 深度报告（单次消耗型）
INSERT INTO shop_products (category_id, sku, name, description, product_type, price_fen, credits_grant, sort_order) VALUES
    ((SELECT id FROM shop_categories WHERE name='深度报告'), 'report_emotion_30d', '30天情绪深度报告', '人工智能生成的30天情绪分析专业报告', 'report', 980, 0, 1),
    ((SELECT id FROM shop_categories WHERE name='深度报告'), 'report_personality', '人格特质报告',     'MBTI+依恋+防御机制综合人格报告',      'report', 1280, 0, 2)
ON CONFLICT (sku) DO NOTHING;
