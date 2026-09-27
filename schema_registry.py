'''
Schema 注册 + 域路由 + 向量检索
'''

import sqlite3
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

DB_PATH = "data.db"

# ============ 5 个业务域 ============
DOMAINS = {
    "基础域": ["regions", "cities", "levels", "categories", "suppliers"],
    "客户域": ["customers", "customer_tags", "customer_addresses",
             "customer_followups", "customer_points"],
    "产品域": ["products", "product_attributes", "product_reviews",
             "product_prices_history", "product_stocks"],
    "销售域": ["orders", "order_details", "order_logs", "order_coupons",
             "order_deliveries", "order_returns", "order_refunds",
             "order_sources", "order_source_map", "order_ratings"],
    "库存域": ["warehouses", "inventory", "inventory_logs",
             "inventory_checks", "inventory_transfers"],
    "财务域": ["payments", "invoices", "expenses", "revenues", "budgets"],
}

# ============ 50 张表的业务描述 ============
TABLE_DESCRIPTIONS = {
    "regions": "地区表，包含地区ID和地区名称（华北/华东/华南/西南/华中）",
    "cities": "城市表，包含城市ID、城市名称、所属地区ID",
    "levels": "客户等级表，包含等级ID、等级名称（普通/银牌/金牌/钻石）、折扣率",
    "categories": "产品类别表，包含类别ID、类别名称（电子产品/家居/服饰/食品/图书）",
    "suppliers": "供应商表，包含供应商ID、供应商名称、联系人",
    "customers": "客户表，包含客户ID、姓名、所在城市ID、等级ID、注册日期",
    "customer_tags": "客户标签表，包含标签ID、客户ID、标签名称（高价值/活跃/流失风险/新客/VIP）",
    "customer_addresses": "客户地址表，包含地址ID、客户ID、详细地址、是否默认",
    "customer_followups": "客户跟进表，包含跟进ID、客户ID、跟进日期、跟进内容",
    "customer_points": "客户积分表，包含积分ID、客户ID、积分数、更新日期",
    "products": "产品表，包含产品ID、名称、类别ID、供应商ID、价格、上下架状态",
    "product_attributes": "产品属性表，包含属性ID、产品ID、属性名（颜色/尺寸/材质/重量）、属性值",
    "product_reviews": "产品评论表，包含评论ID、产品ID、评分、评论内容、评论日期",
    "product_prices_history": "产品价格历史表，包含历史ID、产品ID、旧价格、新价格、变更日期",
    "product_stocks": "产品库存表，包含库存ID、产品ID、库存数、更新日期",
    "orders": "订单表，包含订单ID、客户ID、下单日期、订单状态、订单总金额",
    "order_details": "订单明细表，包含明细ID、订单ID、产品ID、数量、单价",
    "order_logs": "订单日志表，包含日志ID、订单ID、操作类型、操作时间",
    "order_coupons": "订单优惠券表，包含ID、订单ID、优惠券码、优惠金额",
    "order_deliveries": "订单配送表，包含配送ID、订单ID、快递公司、运单号、配送日期",
    "order_returns": "订单退货表，包含退货ID、订单ID、退货原因、退货日期",
    "order_refunds": "订单退款表，包含退款ID、订单ID、退款金额、退款日期",
    "order_sources": "订单来源表，包含来源ID、来源名称（APP/小程序/网页/线下门店/电话）",
    "order_source_map": "订单来源映射表，包含ID、订单ID、来源ID",
    "order_ratings": "订单评价表，包含评价ID、订单ID、评分",
    "warehouses": "仓库表，包含仓库ID、仓库名称、所在城市ID",
    "inventory": "库存表，包含库存ID、产品ID、仓库ID、库存数量、更新日期",
    "inventory_logs": "库存流水表，包含日志ID、产品ID、仓库ID、变更类型（入库/出库/调拨）、变更数量、变更日期",
    "inventory_checks": "库存盘点表，包含盘点ID、仓库ID、盘点日期、盘点结果",
    "inventory_transfers": "库存调拨表，包含调拨ID、源仓库ID、目标仓库ID、产品ID、数量、调拨日期",
    "payments": "支付表，包含支付ID、订单ID、支付方式（支付宝/微信/银行卡/信用卡）、支付金额、支付日期",
    "invoices": "发票表，包含发票ID、订单ID、发票号、金额、开票日期",
    "expenses": "费用表，包含费用ID、费用类别（办公/差旅/推广/人力）、金额、费用日期",
    "revenues": "收入表，包含收入ID、日期、收入金额",
    "budgets": "预算表，包含预算ID、月份、预算金额",
}

# ============ 表关系（Join 路径）============
TABLE_RELATIONS = {
    "cities": "cities.region_id → regions.region_id",
    "customers": "customers.city_id → cities.city_id\ncustomers.level_id → levels.level_id",
    "customer_tags": "customer_tags.customer_id → customers.customer_id",
    "customer_addresses": "customer_addresses.customer_id → customers.customer_id",
    "customer_followups": "customer_followups.customer_id → customers.customer_id",
    "customer_points": "customer_points.customer_id → customers.customer_id",
    "products": "products.category_id → categories.category_id\nproducts.supplier_id → suppliers.supplier_id",
    "product_attributes": "product_attributes.product_id → products.product_id",
    "product_reviews": "product_reviews.product_id → products.product_id",
    "product_prices_history": "product_prices_history.product_id → products.product_id",
    "product_stocks": "product_stocks.product_id → products.product_id",
    "orders": "orders.customer_id → customers.customer_id",
    "order_details": "order_details.order_id → orders.order_id\norder_details.product_id → products.product_id",
    "order_logs": "order_logs.order_id → orders.order_id",
    "order_coupons": "order_coupons.order_id → orders.order_id",
    "order_deliveries": "order_deliveries.order_id → orders.order_id",
    "order_returns": "order_returns.order_id → orders.order_id",
    "order_refunds": "order_refunds.order_id → orders.order_id",
    "order_source_map": "order_source_map.order_id → orders.order_id\norder_source_map.source_id → order_sources.source_id",
    "order_ratings": "order_ratings.order_id → orders.order_id",
    "warehouses": "warehouses.city_id → cities.city_id",
    "inventory": "inventory.product_id → products.product_id\ninventory.warehouse_id → warehouses.warehouse_id",
    "inventory_logs": "inventory_logs.product_id → products.product_id\ninventory_logs.warehouse_id → warehouses.warehouse_id",
    "inventory_checks": "inventory_checks.warehouse_id → warehouses.warehouse_id",
    "inventory_transfers": "inventory_transfers.from_warehouse_id → warehouses.warehouse_id\ninventory_transfers.to_warehouse_id → warehouses.warehouse_id\ninventory_transfers.product_id → products.product_id",
    "payments": "payments.order_id → orders.order_id",
    "invoices": "invoices.order_id → orders.order_id",
}


def _load_real_schema(table_name: str) -> str:
    """从 SQLite 读取真实字段，生成 Schema 文本"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table_name})")
    cols = cur.fetchall()
    conn.close()

    lines = [f"表名：{table_name}", "字段："]
    for col in cols:
        col_name = col[1]
        col_type = col[2]
        lines.append(f"- {col_name}: {col_type}")
    return "\n".join(lines)


# ============ 域路由器 ============
class DomainRouter:
    def __init__(self, model):
        self.model = model
        self.domain_names = list(DOMAINS.keys())
        self.domain_texts = [
            f"{name}：包含表 " + "、".join(DOMAINS[name])
            for name in self.domain_names
        ]
        vectors = self.model.encode(self.domain_texts, normalize_embeddings=True)
        self.vectors = np.array(vectors).astype("float32")
        self.index = faiss.IndexFlatIP(self.vectors.shape[1])
        self.index.add(self.vectors)

    def route(self, question: str, top_k: int = 3) -> list:
        q_vec = self.model.encode([question], normalize_embeddings=True)
        q_vec = np.array(q_vec).astype("float32")
        scores, indices = self.index.search(q_vec, top_k)
        return [
            {"domain": self.domain_names[i],
             "tables": DOMAINS[self.domain_names[i]],
             "score": float(s)}
            for s, i in zip(scores[0], indices[0]) if i != -1
        ]


### ============ Schema 检索器 ============
class SchemaRetriever:
    def __init__(self, model_name: str = "BAAI/bge-small-zh-v1.5"):  #使用远程模型
        print(f"📦 加载 Embedding 模型：{model_name} ...")
        self.model = SentenceTransformer(model_name)
        self.router = DomainRouter(self.model)
        self.table_names = list(TABLE_DESCRIPTIONS.keys())
        self._build_index()
        print(f"✅ Schema 索引构建完成，共 {len(self.table_names)} 张表")

    def _build_index(self):
        descriptions = [TABLE_DESCRIPTIONS[t] for t in self.table_names]
        vectors = self.model.encode(descriptions, normalize_embeddings=True)
        vectors = np.array(vectors).astype("float32")
        self.index = faiss.IndexFlatIP(vectors.shape[1])
        self.index.add(vectors)

# ######################################## 以下是本地化 #################################
# import requests
#
# class OllamaEmbedder:
#     """用 Ollama 的 /api/embed 接口做 Embedding"""
#
#     def __init__(self, model: str = "bge-m3:latest",
#                  base_url: str = "http://localhost:11434"):
#         self.model = model
#         self.base_url = base_url
#
#     def encode(self, texts, normalize_embeddings: bool = True):
#         """兼容 SentenceTransformer 的 encode 接口"""
#         if isinstance(texts, str):
#             texts = [texts]
#
#         resp = requests.post(
#             f"{self.base_url}/api/embed",
#             json={"model": self.model, "input": texts},
#             timeout=60
#         )
#         resp.raise_for_status()
#         vectors = np.array(resp.json()["embeddings"]).astype("float32")
#
#         if normalize_embeddings:
#             norms = np.linalg.norm(vectors, axis=1, keepdims=True)
#             vectors = vectors / np.clip(norms, 1e-12, None)
#         return vectors
#
# class SchemaRetriever:
#     def __init__(self, model_name: str = "bge-m3:latest"):
#         print(f"📦 加载 Embedding 模型：{model_name}（Ollama）...")
#         self.model = OllamaEmbedder(model=model_name)
#         self.router = DomainRouter(self.model)
#         self.table_names = list(TABLE_DESCRIPTIONS.keys())
#         self._build_index()
#         print(f"✅ Schema 索引构建完成，共 {len(self.table_names)} 张表")
#
#     def _build_index(self):
#         descriptions = [TABLE_DESCRIPTIONS[t] for t in self.table_names]
#         vectors = self.model.encode(descriptions, normalize_embeddings=True)
#         self.index = faiss.IndexFlatIP(vectors.shape[1])
#         self.index.add(vectors)
# ######################################## 以上是本地化 #################################

    def retrieve(self, question: str, top_k: int = 6,
                 use_router: bool = True) -> list:
        # 1. 域路由
        if use_router:
            domains = self.router.route(question, top_k=3)
            candidate_tables = []
            for d in domains:
                for t in d["tables"]:
                    if t not in candidate_tables:
                        candidate_tables.append(t)
            print(f"🎯 域路由：{[d['domain'] for d in domains]}")
        else:
            candidate_tables = self.table_names

        # 2. 在候选表里做向量检索
        candidate_indices = [self.table_names.index(t) for t in candidate_tables]
        q_vec = self.model.encode([question], normalize_embeddings=True)
        q_vec = np.array(q_vec).astype("float32")

        # 从完整索引中取出候选表的向量
        all_vectors = np.zeros((self.index.ntotal, self.index.d), dtype="float32")
        for i in range(self.index.ntotal):
            all_vectors[i] = self.index.reconstruct(i)
        candidate_vectors = all_vectors[candidate_indices]

        temp_index = faiss.IndexFlatIP(candidate_vectors.shape[1])
        temp_index.add(candidate_vectors)
        scores, indices = temp_index.search(q_vec, min(top_k, len(candidate_tables)))

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            table_name = candidate_tables[idx]
            results.append({
                "table": table_name,
                "description": TABLE_DESCRIPTIONS[table_name],
                "schema": _load_real_schema(table_name),
                "relations": TABLE_RELATIONS.get(table_name, ""),
                "score": float(score)
            })
        return results

    @staticmethod
    def build_schema_text(tables: list) -> str:
        return "\n\n".join([t["schema"] for t in tables])

    @staticmethod
    def build_relations_text(tables: list) -> str:
        relations = [t["relations"] for t in tables if t["relations"]]
        return "\n".join(relations)
