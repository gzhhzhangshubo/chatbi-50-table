'''
前后端功能合并在一起

'''

import sys
sys.path.append('.')

import os
import re
import time
import uuid
import hashlib
import sqlite3
from typing import Optional, List

import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px

# ============================================================
# 自动生成数据库（云端首次运行需要）
# ============================================================
if not os.path.exists("data.db"):
    import init_db

# ============================================================
# 配置
# ============================================================
# 优先从 Streamlit Secrets 读 Key，其次从环境变量读
try:
    DEEPSEEK_API_KEY = st.secrets["DEEPSEEK_API_KEY"]
except Exception:
    DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-chat"
DB_PATH = "data.db"

from openai import OpenAI
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

from schema_registry import SchemaRetriever
retriever = SchemaRetriever()

# ============================================================
# Few-shot 示例
# ============================================================
FEW_SHOTS = [
    {
        "question": "各个地区的订单总金额",
        "sql": """SELECT r.region_name, SUM(o.total_amount) AS total_amount
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
JOIN cities ci ON c.city_id = ci.city_id
JOIN regions r ON ci.region_id = r.region_id
GROUP BY r.region_name
ORDER BY total_amount DESC;"""
    },
    {
        "question": "销售额最高的5个产品",
        "sql": """SELECT p.product_name, SUM(od.quantity * od.unit_price) AS total_sales
FROM order_details od
JOIN products p ON od.product_id = p.product_id
GROUP BY p.product_name
ORDER BY total_sales DESC
LIMIT 5;"""
    },
    {
        "question": "每个仓库的库存总量",
        "sql": """SELECT w.warehouse_name, SUM(i.quantity) AS total_quantity
FROM inventory i
JOIN warehouses w ON i.warehouse_id = w.warehouse_id
GROUP BY w.warehouse_name
ORDER BY total_quantity DESC;"""
    },
    {
        "question": "各支付方式的订单总金额",
        "sql": """SELECT payment_method, SUM(payment_amount) AS total
FROM payments
GROUP BY payment_method
ORDER BY total DESC;"""
    }
]

# ============================================================
# 缓存层
# ============================================================
class ResponseCache:
    def __init__(self, ttl: int = 3600, max_size: int = 1000):
        self.cache = {}
        self.ttl = ttl
        self.max_size = max_size
        self.hits = 0
        self.misses = 0

    def _make_key(self, question: str, history: list) -> str:
        history_str = "|".join([h["question"] for h in history[-2:]])
        raw = f"{question}||{history_str}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def get(self, question: str, history: list):
        key = self._make_key(question, history)
        if key not in self.cache:
            self.misses += 1
            return None
        value, expire = self.cache[key]
        if time.time() > expire:
            del self.cache[key]
            self.misses += 1
            return None
        self.hits += 1
        return value

    def set(self, question: str, history: list, value):
        if len(self.cache) >= self.max_size:
            sorted_items = sorted(self.cache.items(), key=lambda x: x[1][1])
            for k, _ in sorted_items[:int(self.max_size * 0.2)]:
                del self.cache[k]
        key = self._make_key(question, history)
        self.cache[key] = (value, time.time() + self.ttl)

    def clear(self):
        self.cache.clear()
        self.hits = 0
        self.misses = 0

cache = ResponseCache()


# ============================================================
# 核心函数（从 main.py 搬过来）
# ============================================================
def _clean_sql(sql: str) -> str:
    sql = sql.replace("```sql", "").replace("```", "").strip()
    if ";" in sql:
        sql = sql[:sql.index(";") + 1]
    return sql


def generate_sql(question: str, history=None) -> tuple:
    relevant_tables = retriever.retrieve(question, top_k=6)
    schema_text = retriever.build_schema_text(relevant_tables)
    relations_text = retriever.build_relations_text(relevant_tables)
    table_names = [t["table"] for t in relevant_tables]

    messages = [{
        "role": "system",
        "content": f"""你是一个专业的 SQL 生成助手。根据用户问题和数据库 Schema，生成一条 SQLite 查询语句。

规则：
1. 只输出 SQL，不要输出任何解释
2. 使用标准 SQLite 语法
3. 字段名和表名必须与 Schema 一致
4. 需要跨表查询时使用 JOIN，参考「表关系」中的外键路径
5. 避免 SELECT *，只查询需要的字段
6. 聚合查询必须加 GROUP BY
7. 日期字段是字符串 YYYY-MM-DD

数据库 Schema：
{schema_text}

表关系（Join 路径）：
{relations_text}"""
    }]

    for shot in FEW_SHOTS:
        messages.append({"role": "user", "content": shot["question"]})
        messages.append({"role": "assistant", "content": shot["sql"]})

    if history:
        for h in history[-4:]:
            messages.append({"role": "user", "content": h["question"]})
            messages.append({"role": "assistant", "content": h["sql"]})

    messages.append({"role": "user", "content": question})

    resp = client.chat.completions.create(
        model=MODEL, messages=messages, temperature=0.1, max_tokens=800
    )
    sql = _clean_sql(resp.choices[0].message.content)
    return sql, table_names


def fix_sql(question: str, sql: str, error: str) -> str:
    relevant_tables = retriever.retrieve(question, top_k=6)
    schema_text = retriever.build_schema_text(relevant_tables)
    relations_text = retriever.build_relations_text(relevant_tables)

    prompt = f"""以下 SQL 执行报错，请修正：

问题：{question}
原 SQL：{sql}
错误信息：{error}

数据库 Schema：
{schema_text}

表关系：
{relations_text}

请只输出修正后的 SQL，不要解释。"""

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )
    return _clean_sql(resp.choices[0].message.content)


FORBIDDEN = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER",
             "TRUNCATE", "CREATE", "REPLACE", "GRANT", "REVOKE"]


def validate_sql(sql: str):
    upper = sql.upper()
    for kw in FORBIDDEN:
        if re.search(rf"\b{kw}\b", upper):
            return False, f"禁止使用 {kw}"
    if not upper.strip().startswith("SELECT"):
        return False, "只允许 SELECT 查询"
    if ";" in sql.strip()[:-1]:
        return False, "不允许多语句执行"
    return True, ""


def execute_sql(sql: str):
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(sql, conn)
        conn.close()
        return df, None
    except Exception as e:
        return None, str(e)


def interpret(question: str, sql: str, df: pd.DataFrame) -> str:
    preview = df.head(20).to_string()
    prompt = f"""用户问题：{question}
执行的 SQL：{sql}
查询结果（共 {len(df)} 行，预览前 20 行）：
{preview}

请用简洁的中文总结查询结果，突出关键发现，控制在 150 字以内。"""
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    return resp.choices[0].message.content.strip()


def recommend_chart(df: pd.DataFrame) -> dict:
    if df is None or df.empty:
        return {"type": "none"}
    cols = df.columns.tolist()
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    datetime_cols = df.select_dtypes(include=["datetime"]).columns.tolist()

    if datetime_cols and numeric_cols:
        return {"type": "line", "x": datetime_cols[0], "y": numeric_cols[0]}
    if len(cols) >= 2 and numeric_cols:
        category_col = [c for c in cols if c not in numeric_cols]
        if category_col:
            return {"type": "bar", "x": category_col[0], "y": numeric_cols[0]}
    return {"type": "table"}


# ============================================================
# 核心处理函数（原来是 /chat 接口的逻辑）
# ============================================================
def process_question(question: str, session: dict) -> dict:
    """处理一个问题，返回结果字典"""
    history = session["history"]

    # 1. 查缓存
    cached = cache.get(question, history)
    if cached:
        history.append({"question": question, "sql": cached["sql"]})
        cached["cached"] = True
        return cached

    # 2. 生成 SQL
    sql, table_names = generate_sql(question, history)

    # 3. 安全校验
    valid, err = validate_sql(sql)
    if not valid:
        raise Exception(f"SQL 校验失败：{err}")

    # 4. 执行
    df, exec_err = execute_sql(sql)

    # 5. 失败则纠错
    if exec_err:
        sql = fix_sql(question, sql, exec_err)
        df, exec_err = execute_sql(sql)
        if exec_err:
            raise Exception(f"SQL 执行失败：{exec_err}")

    # 6. 解读
    summary = interpret(question, sql, df)

    # 7. 图表
    chart_config = recommend_chart(df)

    # 8. 写缓存
    result = {
        "sql": sql,
        "data": df.head(100).to_dict(orient="records"),
        "summary": summary,
        "chart_config": chart_config,
        "retrieved_tables": table_names,
        "cached": False
    }
    cache.set(question, history, {
        "sql": result["sql"],
        "data": result["data"],
        "summary": result["summary"],
        "chart_config": result["chart_config"],
        "retrieved_tables": result["retrieved_tables"],
    })
    history.append({"question": question, "sql": sql})

    return result


# ============================================================
# Streamlit 界面
# ============================================================
st.set_page_config(page_title="Chat BI 50 Tables", layout="wide")
st.title("💬 Chat BI - 50 表对话式数据分析")

if "session" not in st.session_state:
    st.session_state.session = {"history": []}
if "messages" not in st.session_state:
    st.session_state.messages = []

# ============ 侧边栏 ============
with st.sidebar:
    st.header("📊 数据表（共 50 张）")
    st.markdown("""
    **基础域（5）**：regions, cities, levels, categories, suppliers

    **客户域（5）**：customers, customer_tags, customer_addresses,
    customer_followups, customer_points

    **产品域（5）**：products, product_attributes, product_reviews,
    product_prices_history, product_stocks

    **销售域（10）**：orders, order_details, order_logs, order_coupons,
    order_deliveries, order_returns, order_refunds, order_sources,
    order_source_map, order_ratings

    **库存域（5）**：warehouses, inventory, inventory_logs,
    inventory_checks, inventory_transfers

    **财务域（5）**：payments, invoices, expenses, revenues, budgets
    """)
    if st.button("清空对话"):
        st.session_state.messages = []
        st.session_state.session = {"history": []}
        st.rerun()

# ============ 展示历史消息 ============
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message("user"):
        st.write(msg["question"])
    with st.chat_message("assistant"):
        st.write(msg["summary"])
        with st.expander("🔍 检索到的表"):
            st.write(msg.get("retrieved_tables", []))
        with st.expander("查看 SQL"):
            st.code(msg["sql"], language="sql")
        if msg.get("data"):
            df = pd.DataFrame(msg["data"])
            st.dataframe(df)
            cfg = msg.get("chart_config", {})
            if cfg.get("type") == "bar":
                st.plotly_chart(
                    px.bar(df, x=cfg["x"], y=cfg["y"]),
                    use_container_width=True,
                    key=f"history_bar_{i}"
                )
            elif cfg.get("type") == "line":
                st.plotly_chart(
                    px.line(df, x=cfg["x"], y=cfg["y"]),
                    use_container_width=True,
                    key=f"history_line_{i}"
                )

# ============ 输入框 ============
question = st.chat_input("请输入你的数据问题，例如：各个地区的订单总金额是多少？")

if question:
    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        with st.spinner("正在分析..."):
            try:
                result = process_question(question, st.session_state.session)

                if result.get("cached"):
                    st.info("⚡ 来自缓存（未调用 LLM）")

                st.write(result["summary"])

                with st.expander("🔍 检索到的表"):
                    st.write(result.get("retrieved_tables", []))

                with st.expander("查看 SQL"):
                    st.code(result["sql"], language="sql")

                df = pd.DataFrame(result["data"])
                st.dataframe(df)

                cfg = result.get("chart_config", {})
                current_idx = len(st.session_state.messages)
                if cfg.get("type") == "bar":
                    st.plotly_chart(
                        px.bar(df, x=cfg["x"], y=cfg["y"]),
                        use_container_width=True,
                        key=f"current_bar_{current_idx}"
                    )
                elif cfg.get("type") == "line":
                    st.plotly_chart(
                        px.line(df, x=cfg["x"], y=cfg["y"]),
                        use_container_width=True,
                        key=f"current_line_{current_idx}"
                    )

                st.session_state.messages.append({
                    "question": question,
                    "summary": result["summary"],
                    "sql": result["sql"],
                    "data": result["data"],
                    "chart_config": cfg,
                    "retrieved_tables": result.get("retrieved_tables", [])
                })
            except Exception as e:
                st.error(f"出错了：{e}")