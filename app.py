'''
Streamlit 前端
有缓存机制
'''
sys.path.append('.')
import streamlit as st
import requests
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Chat BI 50 Tables", layout="wide")
st.title("💬 Chat BI - 50 表对话式数据分析")

if "session_id" not in st.session_state:
    st.session_state.session_id = None
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
        st.session_state.session_id = None
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
                resp = requests.post(
                    "http://localhost:8000/chat",
                    json={"question": question,
                          "session_id": st.session_state.session_id},
                    timeout=300
                )
                if resp.status_code != 200:
                    st.error(f"后端报错：{resp.text}")
                else:
                    result = resp.json()
                    st.session_state.session_id = result["session_id"]

                    # 缓存标记
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