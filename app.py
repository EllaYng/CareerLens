from dotenv import load_dotenv
load_dotenv()
import streamlit as st
import requests
import os
from openai import OpenAI

# 读取 API Key
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# DeepSeek 客户端
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

def search_tavily(query):
    """用 Tavily 搜索相关内容"""
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "max_results": 10,
        "include_raw_content": True
    }
    res = requests.post(url, json=payload)
    return res.json().get("results", [])

def fetch_links(links):
    """抓取用户提供的链接内容"""
    url = "https://api.tavily.com/extract"
    payload = {
        "api_key": TAVILY_API_KEY,
        "urls": links
    }
    res = requests.post(url, json=payload)
    return res.json().get("results", [])

def summarize(content, mode):
    """用 DeepSeek 整理内容"""
    if mode == "search":
        prompt = f"""你是一个求职信息整理助手。
以下是从网络搜索到的求职相关内容，请整理成一份结构化求职指南。
要求：
- 分为「简历准备」「面试技巧」「常见问题」「薪资谈判」等模块
- 提炼共识性建议，去掉重复内容
- 语言简洁，用bullet point呈现

内容如下：
{content}"""
    else:
        prompt = f"""你是一个信息整理助手。
以下是用户提供的链接内容，请整理成一份结构化总结。
要求：
- 提炼核心观点和有用信息
- 按主题分类整理
- 语言简洁，用bullet point呈现

内容如下：
{content}"""

    response = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000
    )
    return response.choices[0].message.content

# 页面设置
st.set_page_config(page_title="求职情报站", page_icon="🎯")
st.title("🎯 求职情报站")
st.caption("整合全网求职经验，生成结构化指南")

# 两个模式的 tab
tab1, tab2 = st.tabs(["🔍 自动搜索模式", "🔗 链接总结模式"])

with tab1:
    st.subheader("输入求职方向，AI 自动搜索整理")
    topic = st.text_input("求职方向", placeholder="例如：AI产品经理、算法工程师、运营岗位")
    if st.button("开始搜索", key="search_btn"):
        if not topic:
            st.warning("请输入求职方向")
        else:
            with st.spinner("正在搜索并整理中..."):
                results = search_tavily(f"{topic} 求职经验 面试技巧")
                content = "\n\n".join([
                    f"标题：{r.get('title')}\n内容：{r.get('raw_content') or r.get('content')}"
                    for r in results
                ])
                summary = summarize(content, mode="search")
            st.markdown("### 📋 求职指南")
            st.markdown(summary)

with tab2:
    st.subheader("粘贴链接，AI 整理成结构化总结")
    links_input = st.text_area("每行一个链接", placeholder="https://...\nhttps://...", height=150)
    if st.button("开始整理", key="links_btn"):
        links = [l.strip() for l in links_input.strip().split("\n") if l.strip()]
        if not links:
            st.warning("请输入至少一个链接")
        else:
            with st.spinner("正在抓取并整理中..."):
                results = fetch_links(links)
                content = "\n\n".join([
                    f"链接：{r.get('url')}\n内容：{r.get('raw_content') or r.get('content')}"
                    for r in results
                ])
                summary = summarize(content, mode="links")
            st.markdown("### 📋 整理结果")
            st.markdown(summary)