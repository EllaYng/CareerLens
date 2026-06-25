import streamlit as st
import os
import json
import plotly.graph_objects as go
import pandas as pd
from openai import OpenAI
import PyPDF2
import re

# 本地开发时从 .env 读取；部署到 Streamlit Cloud 时该文件不存在，
# 用 try/except 避免本地没装 python-dotenv 或没有 .env 文件时报错
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# 读取 API Key：优先从 Streamlit Cloud 的 Secrets 读取，
# 本地开发时回退到环境变量（.env）
DEEPSEEK_API_KEY = st.secrets.get("DEEPSEEK_API_KEY", os.getenv("DEEPSEEK_API_KEY"))

if not DEEPSEEK_API_KEY:
    st.error("⚠️ 未检测到 DEEPSEEK_API_KEY，请检查 Secrets 配置或本地 .env 文件。")
    st.stop()

# DeepSeek 客户端
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

# 页面基础设置
st.set_page_config(page_title="AI职业导航 Agent v2.0", page_icon="🧭", layout="centered")

# 注入自定义样式，提升产品视觉高级感
st.markdown("""
<style>
    .match-banner { background: #EEEDFE; padding: 20px; border-radius: 12px; border-left: 5px solid #534AB7; margin-bottom: 20px; }
    .match-score { font-size: 45px; font-weight: bold; color: #534AB7; line-height: 1; }
    .calc-box { background: #f9f9fb; padding: 15px; border-radius: 8px; border: 1px dashed #AFA9EC; margin: 15px 0; }
    .jd-card { background: #fff; padding: 15px; border-radius: 10px; border: 1px solid #eef; margin-bottom: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
    .gap-card { padding: 15px; border-radius: 10px; border: 1px solid #ffebeb; margin-bottom: 12px; background: #fff; border-left: 4px solid #ff4d4d; }
    .task-card { padding: 15px; border-left: 4px solid #534AB7; background: #f8f9fa; margin-bottom: 15px; border-radius: 0 8px 8px 0; }
    .kpi-tag { background: #E1F5EE; color: #0F6E56; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
    .res-tag { background: #EEEDFE; color: #534AB7; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
</style>
""", unsafe_allow_html=True)

# PDF 解析辅助函数
def extract_text_from_pdf(uploaded_file):
    try:
        reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        return f"无法读取简历内容: {e}"

# JSON 解析与校验函数（四层防护 + 代码端计算）
def parse_llm_json(raw_content):
    # 第一层：剥离 Markdown 代码块（兼容大小写和空格变体）
    clean = re.sub(r'```[\w]*\n?', '', raw_content).strip()

    # 第二层：提取最外层 JSON 对象，去除前置解释文字
    start = clean.find('{')
    end = clean.rfind('}') + 1
    if start == -1 or end == 0:
        raise ValueError("未在模型输出中找到有效的 JSON 结构，请重新诊断。")
    clean = clean[start:end]

    # 第三层：反序列化
    result = json.loads(clean)

    # 第四层：关键字段存在性校验
    required_top = ['jd_profile', 'analysis', 'action_roadmap']
    for key in required_top:
        if key not in result:
            raise ValueError(f"模型输出缺少必要字段：{key}，请重新诊断。")
    if 'calculation_table' not in result['analysis']:
        raise ValueError("模型输出缺少 calculation_table 字段，请重新诊断。")

    table = result['analysis']['calculation_table']
    if not table:
        raise ValueError("模型输出的 calculation_table 为空，请重新诊断。")

    # 第五层（改造后）：由代码自己计算加权分和总分，不再依赖大模型做数学题
    # 大模型只负责给出每个维度的 score（得分）和 weight（权重），
    # weighted_score（加权贡献分）和 match_score（总分）都由 Python 算出来，
    # 这样从根本上消除"模型自己算错"导致的数学不一致问题。
    total_weight = 0
    for row in table:
        score = float(str(row.get('score', 0)).replace('%', ''))
        weight = float(str(row.get('weight', 0)).replace('%', ''))
        row['score'] = score
        row['weight'] = weight
        row['weighted_score'] = round(score * weight / 100, 1)
        total_weight += weight

    # 权重之和应为100，允许 ±2 的误差（模型给的权重小数点凑整偏差）
    if abs(total_weight - 100) > 2:
        raise ValueError(
            f"模型输出的权重之和为 {total_weight:.1f}%，不等于100%，请重新诊断。"
        )

    match_score = round(sum(row['weighted_score'] for row in table), 1)
    result['analysis']['match_score'] = match_score

    # 公式文本同样由代码拼出，而不是用模型生成的文字——
    # 保证公式里显示的维度名称和权重，跟 calculation_table 里实际参与计算的数字
    # 永远保持一致，不会出现"公式写的权重"和"表格权重"不一样的情况。
    formula_parts = [
        f"{row['dimension']}({row['weight']:.0f}%)×得分"
        for row in table
    ]
    result['analysis']['formula'] = "总分 = " + " + ".join(formula_parts)

    return result


# 大模型核心调用函数
def generate_advanced_career_agent(jd_text, resume_text, experience):
    prompt = f"""你是一个顶尖的AI职业规划Agent。
请深度解析用户提供的数据：
1. 目标岗位的招聘JD文本：
\"\"\"{jd_text}\"\"\"

2. 用户的个人简历/背景：
\"\"\"{resume_text}\"\"\"

3. 用户当前工作年限：{experience}

请完成以下三层任务，并严格输出 JSON 格式。不要包含 ```json 等 Markdown 标记，确保其可以直接被 json.loads 解析：
1. 岗位画像：从 JD 中逆向推导其最看重的 5 个核心能力维度及评分、核心高频关键词、以及招聘描述里透露出的典型业务项目。
2. 能力分析：针对每个核心维度，给出用户在该维度的得分（0-100）以及该维度在总分中的权重（5个维度权重之和必须正好等于100%）。**不需要你计算加权分和总分，这部分由系统自动计算**，你只需要给出每个维度的原始得分和权重比例。找出 2-3 个核心 Gap。
3. 落地路线图：针对 Gap，制定前两周（Week 1 和 Week 2）的魔鬼通关计划，必须包含「具体目标」、「核心考点」以及极具可执行性的「验收标准(KPI)」。

JSON 数据结构必须严格如下：
{{
    "jd_profile": {{
        "job_name": "目标岗位名称",
        "core_abilities": {{"维度1": 95, "维度2": 90, "维度3": 85, "维度4": 80, "维度5": 70}},
        "high_frequency_keywords": ["关键词1", "关键词2", "关键词3"],
        "typical_projects": ["项目背景/场景1", "项目背景/场景2"]
    }},
    "analysis": {{
        "calculation_table": [
            {{"dimension": "维度1", "score": 80, "weight": 30}},
            {{"dimension": "维度2", "score": 70, "weight": 25}},
            {{"dimension": "维度3", "score": 60, "weight": 20}},
            {{"dimension": "维度4", "score": 75, "weight": 15}},
            {{"dimension": "维度5", "score": 65, "weight": 10}}
        ],
        "gaps": [
            {{"name": "Gap名称", "desc": "具体能力欠缺描述", "priority": "高"}}
        ]
    }},
    "action_roadmap": [
        {{
            "week": "Week 1",
            "theme": "第一周学习主题",
            "goal": "具体要达到的目标",
            "points": ["核心知识点1", "核心知识点2"],
            "kpi": "具体的验收标准，例如：在LeetCode完成10道题/输出1份PRD文档",
            "resources": ["具体资源/工具1"]
        }}
    ]
}}"""

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=2500
    )
    
    raw_content = response.choices[0].message.content
    return parse_llm_json(raw_content)

# 初始化 Session State 状态机
if "agent_v2_data" not in st.session_state:
    st.session_state.agent_v2_data = None

# UI 架构：定义三大Tab
tab1, tab2, tab3 = st.tabs(["🎯 岗位画像", "📊 匹配度分析", "🗺️ 周级路线图"])

# ================= 侧边栏：输入与配置中心 =================
with st.sidebar:
    st.markdown("### 🧭 AI Agent 配置中心")
    st.caption("在这里输入源数据，驱动下方全链路分析")
    
    experience = st.selectbox("⏳ 你的当前资历", ["应届生（0年）", "初级（1-3年）", "中级（3-5年）", "高级（5年+）"], index=1)
    
    st.markdown("---")
    st.markdown("**1. 粘贴你想投递的岗位 JD**")
    jd_input = st.text_area("直接复制招聘网站(如Boss直聘)的职位描述", height=200, 
                            placeholder="例如：负责大模型Agent产品的设计...熟练掌握SQL...有RAG落地经验者优先...")
    
    st.markdown("---")
    st.markdown("**2. 提供你的个人简历**")
    uploaded_file = st.file_uploader("上传个人简历 (PDF)", type=["pdf"])
    manual_resume = st.text_area("或者直接粘贴你的经历简述", height=150, placeholder="例如：两年开发经验，熟悉Python，但没有独立做过产品经理...")

    st.markdown("---")
    if st.button("🚀 启动全链路 AI 诊断", use_container_width=True, type="primary"):
        resume_text = manual_resume
        if uploaded_file is not None:
            resume_text = extract_text_from_pdf(uploaded_file)
            
        if not jd_input.strip() or not resume_text.strip():
            st.error("❌ 岗位JD 和 个人简历 均为必填项，请补充完整后再行诊断！")
        else:
            with st.spinner("🧠 Agent 正在深度解构岗位需求并交叉对比简历..."):
                try:
                    result = generate_advanced_career_agent(jd_input, resume_text, experience)
                    st.session_state.agent_v2_data = result
                    st.success("✅ 诊断成功！数据已分流至右侧各个看板。")
                except Exception as e:
                    st.error(f"诊断遭遇意外，错误排查: {e}")

# ================= Tab 1: 岗位画像页 =================
with tab1:
    data = st.session_state.agent_v2_data
    if not data:
        st.info("👋 欢迎来到 **AI职业导航 Agent v2.0**！请先在左侧输入 **岗位JD** 和 **个人简历**，并点击「启动全链路 AI 诊断」。")
    else:
        profile = data['jd_profile']
        st.markdown(f"## 🎯 岗位画像：{profile['job_name']}")
        st.caption("AI 帮你想明白：这个岗位到底在招什么样的人？底层硬性指标是什么？")
        
        # 1. 核心能力雷达图
        st.markdown("#### 📡 岗位核心能力大盘")
        abilities = profile['core_abilities']
        df_radar = pd.DataFrame(dict(r=list(abilities.values()), theta=list(abilities.keys())))
        df_radar = pd.concat([df_radar, df_radar.iloc[[0]]]) # 闭合图表
        
        fig = go.Figure(data=go.Scatterpolar(
            r=df_radar['r'], theta=df_radar['theta'], fill='toself',
            line_color='#534AB7', fillcolor='rgba(83, 74, 183, 0.2)'
        ))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=False, margin=dict(l=40, r=40, t=30, b=30))
        st.plotly_chart(fig, use_container_width=True)
        
        # 2. 高频硬考点与典型项目
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("##### 🔑 JD高频关键词 (硬考点)")
            for kw in profile['high_frequency_keywords']:
                st.markdown(f"<div class='jd-card'>🔥 <b>{kw}</b></div>", unsafe_allow_html=True)
        with col2:
            st.markdown("##### 💼 典型业务/项目场景")
            for proj in profile['typical_projects']:
                st.markdown(f"<div class='jd-card'>🧱 {proj}</div>", unsafe_allow_html=True)

# ================= Tab 2: 能力分析页（解密 72%） =================
with tab2:
    data = st.session_state.agent_v2_data
    if not data:
        st.info("💡 请先在左侧完成 AI 诊断。")
    else:
        analysis = data['analysis']
        
        # 1. 匹配度展示
        st.markdown("<div class='match-banner'>", unsafe_allow_html=True)
        st.markdown(f"<span style='font-size:14px; color:#3C3489;'>⚖️ 深度加权复核</span>", unsafe_allow_html=True)
        st.markdown(f"<div class='match-score'>{analysis['match_score']}%</div>", unsafe_allow_html=True)
        st.markdown(f"<p style='margin-top:10px; color:#534AB7; font-size:13px;'><b>计算依据公式：</b><br>{analysis['formula']}</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # 2. 计算明细表
        st.markdown("#### 🔢 维度得分明细表")
        df_calc = pd.DataFrame(analysis['calculation_table'])
        df_calc = df_calc[['dimension', 'score', 'weight', 'weighted_score']]
        df_calc.columns = ["评估维度", "你的得分", "权重占比(%)", "加权贡献分"]
        st.table(df_calc)
        st.caption("加权贡献分 = 你的得分 × 权重占比，由系统自动计算，确保数学准确无误。")
        
        st.divider()
        
        # 3. 核心 Gap 列表
        st.markdown("#### ⚠️ 你的核心能力 Gap 盘点")
        for gap in analysis['gaps']:
            st.markdown(f"""
            <div class="gap-card">
                <strong>⚡ {gap['name']}</strong> <span style="float:right; font-size:11px; background:#fff0f0; color:#ff4d4d; padding:2px 6px; border-radius:4px;">{gap['priority']}优先级</span><br>
                <span style="font-size: 13px; color: #555; display:inline-block; margin-top:6px;">{gap['desc']}</span>
            </div>
            """, unsafe_allow_html=True)

# ================= Tab 3: 成长路线页（落地执行） =================
with tab3:
    data = st.session_state.agent_v2_data
    if not data:
        st.info("💡 请先在左侧完成 AI 诊断。")
    else:
        st.markdown("## 🗺️ 针对性突击行动计划")
        st.info("🏃‍♂️ 别再泛泛而谈！以下是 Agent 为你量身制定的高阶实战通关指标：")
        
        for plan in data['action_roadmap']:
            st.markdown(f"### 🏁 {plan['week']}: {plan['theme']}")
            
            # 拼装核心考点标签
            points_html = "".join([f"<span class='res-tag' style='margin-right:5px;'>📍 {pt}</span>" for pt in plan['points']])
            # 拼装推荐资源
            res_html = "".join([f"<span class='res-tag' style='margin-right:5px; background:#eef;'>🛠️ {res}</span>" for res in plan['resources']])
            
            st.markdown(f"""
            <div class="task-card">
                <p>🎯 <b>魔鬼突击目标：</b>{plan['goal']}</p>
                <p style="margin: 8px 0;">💡 <b>必须吃透的核心考点：</b><br>{points_html}</p>
                <div style="background:#fff; padding:10px; border-radius:6px; border:1px solid #e1f5ee; margin: 10px 0;">
                    <span class="kpi-tag">🏅 唯一验收标准(KPI)</span>
                    <p style="margin-top:5px; font-size:13px; color:#0F6E56; font-weight:bold;">{plan['kpi']}</p>
                </div>
                <p style="margin-top: 8px; font-size:12px;">📚 <b>推荐踩坑资源：</b>{res_html}</p>
            </div>
            """, unsafe_allow_html=True)