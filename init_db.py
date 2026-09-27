'''
生成示例数据
'''
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

np.random.seed(42)

# ============ 基础域（5 张）============
regions = pd.DataFrame({
    "region_id": range(1, 6),
    "region_name": ["华北", "华东", "华南", "西南", "华中"]
})

cities = pd.DataFrame({
    "city_id": range(1, 16),
    "city_name": ["北京", "天津", "上海", "杭州", "南京", "广州", "深圳",
                  "珠海", "成都", "重庆", "武汉", "长沙", "西安", "郑州", "青岛"],
    "region_id": np.random.randint(1, 6, 15)
})

levels = pd.DataFrame({
    "level_id": range(1, 5),
    "level_name": ["普通", "银牌", "金牌", "钻石"],
    "discount": [1.0, 0.95, 0.9, 0.85]
})

categories = pd.DataFrame({
    "category_id": range(1, 6),
    "category_name": ["电子产品", "家居", "服饰", "食品", "图书"]
})

suppliers = pd.DataFrame({
    "supplier_id": range(1, 11),
    "supplier_name": [f"供应商{i}" for i in range(1, 11)],
    "contact": [f"联系人{i}" for i in range(1, 11)]
})

# ============ 客户域（5 张）============
customers = pd.DataFrame({
    "customer_id": range(1, 201),
    "customer_name": [f"客户{i}" for i in range(1, 201)],
    "city_id": np.random.randint(1, 16, 200),
    "level_id": np.random.randint(1, 5, 200),
    "register_date": [
        (datetime(2023, 1, 1) + timedelta(days=int(np.random.randint(0, 730)))).strftime("%Y-%m-%d")
        for _ in range(200)
    ]
})

customer_tags = pd.DataFrame({
    "tag_id": range(1, 51),
    "customer_id": np.random.randint(1, 201, 50),
    "tag_name": np.random.choice(["高价值", "活跃", "流失风险", "新客", "VIP"], 50)
})

customer_addresses = pd.DataFrame({
    "address_id": range(1, 201),
    "customer_id": np.random.randint(1, 201, 200),
    "address": [f"地址{i}" for i in range(1, 201)],
    "is_default": np.random.choice([0, 1], 200)
})

customer_followups = pd.DataFrame({
    "followup_id": range(1, 301),
    "customer_id": np.random.randint(1, 201, 300),
    "followup_date": [
        (datetime(2024, 1, 1) + timedelta(days=int(np.random.randint(0, 730)))).strftime("%Y-%m-%d")
        for _ in range(300)
    ],
    "content": [f"跟进记录{i}" for i in range(1, 301)]
})

customer_points = pd.DataFrame({
    "point_id": range(1, 201),
    "customer_id": np.random.randint(1, 201, 200),
    "points": np.random.randint(0, 10000, 200),
    "update_date": [
        (datetime(2025, 1, 1) + timedelta(days=int(np.random.randint(0, 365)))).strftime("%Y-%m-%d")
        for _ in range(200)
    ]
})

# ============ 产品域（5 张）============
products = pd.DataFrame({
    "product_id": range(1, 51),
    "product_name": [f"产品{i}" for i in range(1, 51)],
    "category_id": np.random.randint(1, 6, 50),
    "supplier_id": np.random.randint(1, 11, 50),
    "price": np.random.randint(50, 3000, 50),
    "status": np.random.choice(["上架", "下架"], 50, p=[0.9, 0.1])
})

product_attributes = pd.DataFrame({
    "attr_id": range(1, 101),
    "product_id": np.random.randint(1, 51, 100),
    "attr_name": np.random.choice(["颜色", "尺寸", "材质", "重量"], 100),
    "attr_value": [f"值{i}" for i in range(1, 101)]
})

product_reviews = pd.DataFrame({
    "review_id": range(1, 501),
    "product_id": np.random.randint(1, 51, 500),
    "rating": np.random.randint(1, 6, 500),
    "comment": [f"评论{i}" for i in range(1, 501)],
    "review_date": [
        (datetime(2024, 1, 1) + timedelta(days=int(np.random.randint(0, 730)))).strftime("%Y-%m-%d")
        for _ in range(500)
    ]
})

product_prices_history = pd.DataFrame({
    "history_id": range(1, 201),
    "product_id": np.random.randint(1, 51, 200),
    "old_price": np.random.randint(50, 3000, 200),
    "new_price": np.random.randint(50, 3000, 200),
    "change_date": [
        (datetime(2024, 1, 1) + timedelta(days=int(np.random.randint(0, 730)))).strftime("%Y-%m-%d")
        for _ in range(200)
    ]
})

product_stocks = pd.DataFrame({
    "stock_id": range(1, 201),
    "product_id": np.random.randint(1, 51, 200),
    "stock": np.random.randint(0, 1000, 200),
    "update_date": [
        (datetime(2025, 1, 1) + timedelta(days=int(np.random.randint(0, 365)))).strftime("%Y-%m-%d")
        for _ in range(200)
    ]
})

# ============ 销售域（10 张）============
orders = pd.DataFrame({
    "order_id": range(1, 2001),
    "customer_id": np.random.randint(1, 201, 2000),
    "order_date": [
        (datetime(2024, 1, 1) + timedelta(days=int(np.random.randint(0, 730)))).strftime("%Y-%m-%d")
        for _ in range(2000)
    ],
    "status": np.random.choice(["待付款", "已付款", "已发货", "已完成", "已取消"],
                               2000, p=[0.05, 0.1, 0.15, 0.65, 0.05]),
    "total_amount": np.random.randint(100, 20000, 2000)
})

order_details = pd.DataFrame({
    "detail_id": range(1, 5001),
    "order_id": np.random.randint(1, 2001, 5000),
    "product_id": np.random.randint(1, 51, 5000),
    "quantity": np.random.randint(1, 10, 5000),
    "unit_price": np.random.randint(50, 3000, 5000)
})

order_logs = pd.DataFrame({
    "log_id": range(1, 3001),
    "order_id": np.random.randint(1, 2001, 3000),
    "action": np.random.choice(["创建", "支付", "发货", "完成", "取消"], 3000),
    "action_time": [
        (datetime(2024, 1, 1) + timedelta(days=int(np.random.randint(0, 730)))).strftime("%Y-%m-%d %H:%M:%S")
        for _ in range(3000)
    ]
})

order_coupons = pd.DataFrame({
    "id": range(1, 1001),
    "order_id": np.random.randint(1, 2001, 1000),
    "coupon_code": [f"CPN{i:05d}" for i in range(1, 1001)],
    "discount_amount": np.random.randint(5, 200, 1000)
})

order_deliveries = pd.DataFrame({
    "delivery_id": range(1, 1501),
    "order_id": np.random.randint(1, 2001, 1500),
    "delivery_company": np.random.choice(["顺丰", "圆通", "中通", "韵达"], 1500),
    "tracking_no": [f"TRK{i:08d}" for i in range(1, 1501)],
    "delivery_date": [
        (datetime(2024, 1, 1) + timedelta(days=int(np.random.randint(0, 730)))).strftime("%Y-%m-%d")
        for _ in range(1500)
    ]
})

order_returns = pd.DataFrame({
    "return_id": range(1, 501),
    "order_id": np.random.randint(1, 2001, 500),
    "reason": np.random.choice(["质量问题", "不喜欢", "发错货", "其他"], 500),
    "return_date": [
        (datetime(2024, 1, 1) + timedelta(days=int(np.random.randint(0, 730)))).strftime("%Y-%m-%d")
        for _ in range(500)
    ]
})

order_refunds = pd.DataFrame({
    "refund_id": range(1, 401),
    "order_id": np.random.randint(1, 2001, 400),
    "refund_amount": np.random.randint(50, 5000, 400),
    "refund_date": [
        (datetime(2024, 1, 1) + timedelta(days=int(np.random.randint(0, 730)))).strftime("%Y-%m-%d")
        for _ in range(400)
    ]
})

order_sources = pd.DataFrame({
    "source_id": range(1, 6),
    "source_name": ["APP", "小程序", "网页", "线下门店", "电话"]
})

order_source_map = pd.DataFrame({
    "id": range(1, 2001),
    "order_id": range(1, 2001),
    "source_id": np.random.randint(1, 6, 2000)
})

order_ratings = pd.DataFrame({
    "rating_id": range(1, 1001),
    "order_id": np.random.randint(1, 2001, 1000),
    "rating": np.random.randint(1, 6, 1000)
})

# ============ 库存域（5 张）============
warehouses = pd.DataFrame({
    "warehouse_id": range(1, 6),
    "warehouse_name": [f"仓库{i}" for i in range(1, 6)],
    "city_id": np.random.randint(1, 16, 5)
})

inventory = pd.DataFrame({
    "inventory_id": range(1, 201),
    "product_id": np.random.randint(1, 51, 200),
    "warehouse_id": np.random.randint(1, 6, 200),
    "quantity": np.random.randint(0, 500, 200),
    "update_date": [
        (datetime(2025, 1, 1) + timedelta(days=int(np.random.randint(0, 365)))).strftime("%Y-%m-%d")
        for _ in range(200)
    ]
})

inventory_logs = pd.DataFrame({
    "log_id": range(1, 501),
    "product_id": np.random.randint(1, 51, 500),
    "warehouse_id": np.random.randint(1, 6, 500),
    "change_type": np.random.choice(["入库", "出库", "调拨"], 500),
    "change_quantity": np.random.randint(-100, 100, 500),
    "change_date": [
        (datetime(2024, 1, 1) + timedelta(days=int(np.random.randint(0, 730)))).strftime("%Y-%m-%d")
        for _ in range(500)
    ]
})

inventory_checks = pd.DataFrame({
    "check_id": range(1, 101),
    "warehouse_id": np.random.randint(1, 6, 100),
    "check_date": [
        (datetime(2024, 1, 1) + timedelta(days=int(np.random.randint(0, 730)))).strftime("%Y-%m-%d")
        for _ in range(100)
    ],
    "result": np.random.choice(["正常", "异常"], 100, p=[0.9, 0.1])
})

inventory_transfers = pd.DataFrame({
    "transfer_id": range(1, 101),
    "from_warehouse_id": np.random.randint(1, 6, 100),
    "to_warehouse_id": np.random.randint(1, 6, 100),
    "product_id": np.random.randint(1, 51, 100),
    "quantity": np.random.randint(1, 100, 100),
    "transfer_date": [
        (datetime(2024, 1, 1) + timedelta(days=int(np.random.randint(0, 730)))).strftime("%Y-%m-%d")
        for _ in range(100)
    ]
})

# ============ 财务域（5 张）============
payments = pd.DataFrame({
    "payment_id": range(1, 1501),
    "order_id": np.random.randint(1, 2001, 1500),
    "payment_method": np.random.choice(["支付宝", "微信", "银行卡", "信用卡"], 1500),
    "payment_amount": np.random.randint(100, 20000, 1500),
    "payment_date": [
        (datetime(2024, 1, 1) + timedelta(days=int(np.random.randint(0, 730)))).strftime("%Y-%m-%d")
        for _ in range(1500)
    ]
})

invoices = pd.DataFrame({
    "invoice_id": range(1, 1001),
    "order_id": np.random.randint(1, 2001, 1000),
    "invoice_no": [f"INV{i:08d}" for i in range(1, 1001)],
    "amount": np.random.randint(100, 20000, 1000),
    "invoice_date": [
        (datetime(2024, 1, 1) + timedelta(days=int(np.random.randint(0, 730)))).strftime("%Y-%m-%d")
        for _ in range(1000)
    ]
})

expenses = pd.DataFrame({
    "expense_id": range(1, 301),
    "category": np.random.choice(["办公", "差旅", "推广", "人力"], 300),
    "amount": np.random.randint(100, 10000, 300),
    "expense_date": [
        (datetime(2024, 1, 1) + timedelta(days=int(np.random.randint(0, 730)))).strftime("%Y-%m-%d")
        for _ in range(300)
    ]
})

revenues = pd.DataFrame({
    "revenue_id": range(1, 731),
    "date": [
        (datetime(2024, 1, 1) + timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(730)
    ],
    "amount": np.random.randint(1000, 50000, 730)
})

budgets = pd.DataFrame({
    "budget_id": range(1, 13),
    "month": [f"2025-{i:02d}" for i in range(1, 13)],
    "budget_amount": np.random.randint(50000, 200000, 12)
})

# ============ 写入数据库 ============
all_tables = {
    "regions": regions, "cities": cities, "levels": levels,
    "categories": categories, "suppliers": suppliers,
    "customers": customers, "customer_tags": customer_tags,
    "customer_addresses": customer_addresses,
    "customer_followups": customer_followups, "customer_points": customer_points,
    "products": products, "product_attributes": product_attributes,
    "product_reviews": product_reviews, "product_prices_history": product_prices_history,
    "product_stocks": product_stocks,
    "orders": orders, "order_details": order_details, "order_logs": order_logs,
    "order_coupons": order_coupons, "order_deliveries": order_deliveries,
    "order_returns": order_returns, "order_refunds": order_refunds,
    "order_sources": order_sources, "order_source_map": order_source_map,
    "order_ratings": order_ratings,
    "warehouses": warehouses, "inventory": inventory, "inventory_logs": inventory_logs,
    "inventory_checks": inventory_checks, "inventory_transfers": inventory_transfers,
    "payments": payments, "invoices": invoices, "expenses": expenses,
    "revenues": revenues, "budgets": budgets,
}

conn = sqlite3.connect("data.db")
for name, df in all_tables.items():
    df.to_sql(name, conn, if_exists="replace", index=False)
conn.close()

print(f"✅ data.db 生成完毕，共 {len(all_tables)} 张表")







