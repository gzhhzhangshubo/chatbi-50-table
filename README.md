# Chat BI 50-Table

> 基于大语言模型的对话式数据分析工具，支持 50 张表的自然语言查询。

用户用中文提问，系统自动完成 **SQL 生成 → 数据查询 → 结果解读 → 可视化** 全流程，让非技术用户也能轻松做数据分析。

---

## ✨ 核心特性

- **两阶段检索**：域路由 + 向量检索，50 张表中精准定位相关表
- **NL2SQL 三层优化**：Schema 裁剪 + Few-shot + 执行失败自我纠错
- **双模式支持**：云端（DeepSeek）保障质量，本地（Ollama）保障隐私
- **缓存机制**：相同问题不重复调用 LLM，响应从 30 秒降到 1 秒
- **SQL 安全校验**：关键字黑名单 + 单语句限制，防止注入
- **多轮会话**：结合上下文理解追问，如「那华南呢？」
- **智能图表**：根据字段类型自动推荐柱状图 / 折线图 / 表格

---

## 🏗️ 系统架构
<img width="1352" height="1296" alt="image" src="https://github.com/user-attachments/assets/2f72b9c1-57a9-4bc2-bc34-8387a4a67ffe" />
系统流程：
<img width="988" height="1652" alt="image" src="https://github.com/user-attachments/assets/24099bfc-8df1-4c4d-8ae4-deaa5b1eee65" />
## 📊 数据模型

模拟电商场景，共 **50 张表**，覆盖 **6 个业务域**：

| 业务域 | 表数量 | 代表表 |
|---|---|---|
| 基础域 | 5 | regions、cities、levels、categories、suppliers |
| 客户域 | 5 | customers、customer_tags、customer_points |
| 产品域 | 5 | products、product_reviews、product_stocks |
| 销售域 | 10 | orders、order_details、order_deliveries |
| 库存域 | 5 | warehouses、inventory、inventory_logs |
| 财务域 | 5 | payments、invoices、expenses、revenues、budgets |

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install fastapi uvicorn streamlit openai pandas numpy plotly requests sqlalchemy faiss-cpu sentence-transformers



**2. 生成示例数据**
方式一：环境变量（推荐）
bash

# Windows PowerShell
$env:DEEPSEEK_API_KEY="sk-你的真实key"

# Linux / Mac
export DEEPSEEK_API_KEY="sk-你的真实key"

方式二：本地 Ollama（无需 API Key）

修改 main.py：
python

LOCAL_BASE_URL = "http://localhost:11434/v1"
LOCAL_API_KEY = "ollama"
MODEL = "qwen2.5:7b"
client = OpenAI(api_key=LOCAL_API_KEY, base_url=LOCAL_BASE_URL)

4. 启动服务

窗口 1：后端
bash

uvicorn main:app --reload --port 8000

窗口 2：前端
bash

streamlit run app.py

浏览器打开 http://localhost:8501。

使用示例
问题	涉及表
各个地区的订单总金额	orders + customers + cities + regions
销售额最高的5个产品	order_details + products
金牌客户的消费总额	orders + customers + levels
每个仓库的库存总量	inventory + warehouses
各支付方式的总金额	payments
北京客户的订单数量	orders + customers + cities
电子产品类别的平均价格	products + categories
退货率最高的产品	order_returns + order_details + products



