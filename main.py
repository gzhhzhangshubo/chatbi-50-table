'''
FastAPI 后端
有缓存机制
'''

import os
import re
import json
import time
import uuid
import hashlib
import sqlite3
from typing import Optional, List

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI

from schema_registry import SchemaRetriever

# ============================================================
# 配置
# ============================================================
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-chat"
DB_PATH = "data.db"
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

# # ============ 本地 Ollama 配置 ============
# LOCAL_BASE_URL = "http://localhost:11434/v1"
# LOCAL_API_KEY = "ollama"          # 本地服务不校验，随便填
# MODEL = "qwen2.5:1.5b"              # 你下载的模型名
# DB_PATH = "data.db"
# client = OpenAI(api_key=LOCAL_API_KEY, base_url=LOCAL_BASE_URL)


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
    """内存缓存，key = 问题 + 最近 2 轮历史"""

    def __init__(self, ttl: int = 3600, max_size: int = 1000):
        self.cache = {}          # key -> (value, expire_time)
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
            # LRU：删掉最早过期的 20%
            sorted_items = sorted(self.cache.items(), key=lambda x: x[1][1])
            for k, _ in sorted_items[:int(self.max_size * 0.2)]:
                del self.cache[k]
        key = self._make_key(question, history)
        self.cache[key] = (value, time.time() + self.ttl)

    def clear(self):
        self.cache.clear()
        self.hits = 0
        self.misses = 0

    def stats(self):
        total = self.hits + self.misses
        hit_rate = (self.hits / total) if total > 0 else 0.0
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "ttl": self.ttl,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate, 4)
        }


cache = ResponseCache(ttl=3600, max_size=1000)


# ============================================================
# SQL 工具函数
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

    print(f"🔍 检索到 {len(table_names)} 张表：{table_names}")

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
# FastAPI
# ============================================================
app = FastAPI(title="Chat BI 50-Table API with Cache")
sessions = {}


class ChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    sql: str
    data: list
    summary: str
    chart_config: dict
    retrieved_tables: list
    cached: bool = False
    error: Optional[str] = None


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())
    session = sessions.setdefault(session_id, {"history": []})

    # ============ 1. 先查缓存 ============
    cached = cache.get(req.question, session["history"])
    if cached:
        print(f"⚡ 缓存命中：{req.question[:40]}")
        session["history"].append({
            "question": req.question,
            "sql": cached["sql"]
        })
        return ChatResponse(
            session_id=session_id,
            sql=cached["sql"],
            data=cached["data"],
            summary=cached["summary"],
            chart_config=cached["chart_config"],
            retrieved_tables=cached["retrieved_tables"],
            cached=True
        )

    print(f"❌ 缓存未命中：{req.question[:40]}，调用 LLM...")

    # ============ 2. 生成 SQL ============
    sql, table_names = generate_sql(req.question, session["history"])

    # ============ 3. 安全校验 ============
    valid, err = validate_sql(sql)
    if not valid:
        raise HTTPException(400, f"SQL 校验失败：{err}")

    # ============ 4. 执行 ============
    df, exec_err = execute_sql(sql)
    if exec_err:
        sql = fix_sql(req.question, sql, exec_err)
        df, exec_err = execute_sql(sql)
        if exec_err:
            raise HTTPException(500, f"SQL 执行失败：{exec_err}")

    # ============ 5. 解读 ============
    summary = interpret(req.question, sql, df)

    # ============ 6. 图表 ============
    chart_config = recommend_chart(df)

    # ============ 7. 写缓存 ============
    cache_value = {
        "sql": sql,
        "data": df.head(100).to_dict(orient="records"),
        "summary": summary,
        "chart_config": chart_config,
        "retrieved_tables": table_names
    }
    cache.set(req.question, session["history"], cache_value)

    # ============ 8. 记录历史 ============
    session["history"].append({"question": req.question, "sql": sql})

    return ChatResponse(
        session_id=session_id,
        sql=sql,
        data=cache_value["data"],
        summary=summary,
        chart_config=chart_config,
        retrieved_tables=table_names,
        cached=False
    )


# ============ 辅助接口 ============
@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "50-Table Chat BI API with Cache is running",
        "tables": len(retriever.table_names)
    }


@app.get("/tables")
def list_tables():
    from schema_registry import TABLE_DESCRIPTIONS
    return {"tables": list(TABLE_DESCRIPTIONS.keys())}


@app.post("/cache/clear")
def clear_cache():
    cache.clear()
    return {"status": "ok", "message": "缓存已清空"}


@app.get("/cache/stats")
def cache_stats():
    return cache.stats()

