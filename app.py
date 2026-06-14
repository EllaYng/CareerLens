from dotenv import load_dotenv
load_dotenv()
import streamlit as st
import os
import json
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from openai import OpenAI
import PyPDF2

# 读取 API Key
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# DeepSeek 客户端
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

# 页面设置
st.set_page_config(page_title="AI职业导航 Agent", page_icon="🧭", layout="centered")

# 自定义一些基础 CSS 来贴近你的原型风格
st.markdown("""
<style>
    .match-score {font-size: 40px; font-weight: bold; color: #534AB7;}
    .gap-card {padding: 15px; border-radius: 10px; border: 1px solid #eee; margin-bottom: 10px; background: #fff;}
    .task-card {padding: 10px; border-left: 4px solid #534AB7; background: #f8f9fa; margin-bottom: 10px;}
    .res-tag {background: #EEEDFE; color: #534AB7; padding: 3px 8px; border-radius: 10px; font-size: 12px; margin-right: 5px;}
</style>
""", unsafe_allow_html=True)

# 提取 PDF 文本的辅助函数
def extract_text_from_pdf(uploaded_file):
    try:
        reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return f"无法读取简历内容: {e}"

# 调用 DeepSeek 进行分析
def generate_career_analysis(target_job, experience, resume_text):
    prompt = f"""你是一个专业的AI职业规划Agent。
用户的目标岗位是：{target_job}
工作经验：{experience}
用户的简历/背景简述如下：
{resume_text}

请分析该用户与目标岗位的匹配度，并输出严格的 JSON 格式数据。请直接返回JSON，不要包含```json等Markdown标记。数据结构必须严格如下：
{{
    "match_score": 72,
    "radar_data": {{"产品思维": 90, "数据分析": 69, "AI认知": 77, "项目管理": 60, "用户研究": 52, "商业分析": 52}},
    "gaps": [
        {{"name": "数据驱动决策", "desc": "SQL查询与A/B实验设计能力不足", "priority": "高", "color": "red"}},
        {{"name": "商业分析框架", "desc": "竞品分析和商业模式理解", "priority": "低", "color": "green"}}
    ],
    "roadmap": [
        {{
            "phase": "30天 · 夯实基础",
            "tasks": [
                {{"name": "SQL 与数据分析入门", "meta": "每天1小时 · 预计20天完成", "resources": ["慕课网SQL课", "Mode实操"]}}
            ]
        }}
    ]
}}
请根据用户简历和岗位要求，生成真实合理的分析内容。"""

    response = client.chat.completions.create(
        model="deepseek-chat", # 使用基础模型或 flash 模型
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3, # 降低随机性，保证结构稳定
        max_tokens=2000
    )
    
    raw_content = response.choices[0].message.content
    # 清理可能存在的 markdown 标记
    clean_content = raw_content.replace('```json', '').replace('```', '').strip()
    return json.loads(clean_content)

# 初始化 Session State
if "analysis_data" not in st.session_state:
    st.session_state.analysis_data = None

# UI 布局：三个 Tabs
tab1, tab2, tab3 = st.tabs(["🏠 首页配置", "📊 能力分析", "🗺️ 成长路线"])

# ================= Tab 1: 首页 =================
with tab1:
    st.markdown("<h2 style='text-align: center;'>🧭 AI职业导航</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>智能分析，精准规划你的职业路径</p>", unsafe_allow_html=True)
    
    target_job = st.text_input("🎯 目标岗位", value="AI产品经理")
    experience = st.selectbox("⏳ 工作年限", ["应届生（0年）", "初级（1-3年）", "中级（3-5年）", "高级（5年+）"], index=1)
    
    uploaded_file = st.file_uploader("📄 上传简历 (PDF)", type=["pdf"])
    manual_resume = st.text_area("或者直接粘贴你的简历/背景简述", height=150, placeholder="例如：某大学计算机系毕业，做过半年后端开发，熟悉Python...")
    
    if st.button("✨ 开始AI诊断", use_container_width=True, type="primary"):
        resume_text = manual_resume
        if uploaded_file is not None:
            resume_text = extract_text_from_pdf(uploaded_file)
            
        if not resume_text.strip():
            st.warning("请提供简历或背景描述，以便AI进行精准分析！")
        else:
            with st.spinner("🧠 正在深度解析你的背景与岗位要求的匹配度..."):
                try:
                    result = generate_career_analysis(target_job, experience, resume_text)
                    st.session_state.analysis_data = result
                    st.success("✅ 分析完成！请点击上方「📊 能力分析」和「🗺️ 成长路线」查看结果。")
                except Exception as e:
                    st.error(f"分析失败，请重试。错误信息: {e}")

# ================= Tab 2: 能力分析 =================
with tab2:
    data = st.session_state.analysis_data
    if not data:
        st.info("请先在首页完成 AI 诊断。")
    else:
        # 1. 匹配度横幅
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown(f"<div class='match-score'>{data['match_score']}%</div>", unsafe_allow_html=True)
            st.write("**岗位匹配度**")
        with col2:
            st.write(f"目标：85% | 当前：{data['match_score']}%")
            st.progress(data['match_score'] / 100.0)
            st.caption(f"还差 {85 - data['match_score']}% 达到核心要求")
        
        st.divider()
        
        # 2. 雷达图
        st.markdown("#### 📡 能力雷达图")
        radar_dict = data['radar_data']
        df_radar = pd.DataFrame(dict(
            r=list(radar_dict.values()),
            theta=list(radar_dict.keys())
        ))
        df_radar = pd.concat([df_radar, df_radar.iloc[[0]]]) # 闭合雷达图
        
        fig = go.Figure(data=go.Scatterpolar(
          r=df_radar['r'],
          theta=df_radar['theta'],
          fill='toself',
          line_color='#534AB7',
          fillcolor='rgba(83, 74, 183, 0.3)'
        ))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=False, margin=dict(l=40, r=40, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        
        # 3. 能力 Gap 列表
        st.markdown("#### ⚠️ 能力 Gap 列表")
        for gap in data['gaps']:
            color_map = {"高": "🔴", "中": "🟡", "低": "🟢"}
            icon = color_map.get(gap.get("priority", "中"), "🔵")
            st.markdown(f"""
            <div class="gap-card">
                <strong>{icon} {gap['name']}</strong> <span style="float:right; font-size:12px; color:gray;">{gap['priority']}优先级</span><br>
                <span style="font-size: 14px; color: #666;">{gap['desc']}</span>
            </div>
            """, unsafe_allow_html=True)

# ================= Tab 3: 成长路线 =================
with tab3:
    data = st.session_state.analysis_data
    if not data:
        st.info("请先在首页完成 AI 诊断。")
    else:
        st.info("💡 基于你的能力分析，AI 为你生成了以下个性化学习路线")
        
        for phase in data['roadmap']:
            st.markdown(f"### 🚩 {phase['phase']}")
            for task in phase['tasks']:
                resources_html = "".join([f"<span class='res-tag'>🏷️ {res}</span>" for res in task['resources']])
                st.markdown(f"""
                <div class="task-card">
                    <strong>{task['name']}</strong><br>
                    <span style="font-size: 12px; color: gray;">{task['meta']}</span><br>
                    <div style="margin-top: 8px;">{resources_html}</div>
                </div>
                """, unsafe_allow_html=True)
            st.write("") # 增加间距