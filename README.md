# 🧭 CareerLens · AI职业导航Agent v2.0

> 拒绝黑盒评分，拒绝鸡汤建议。输入真实JD + 你的简历，得到可执行的职业诊断报告。

![截图](docs/screenshots/02_analysis.png)

## 为什么做这个

市面上的AI求职工具有三个共同问题：

- **岗位定义模糊**：只输入"AI产品经理"四个字，分析结果对谁都适用，对你没用
- **评分黑盒化**：系统输出72%，你不知道怎么算出来的，凭什么信它
- **建议鸡汤化**："建议学习SQL"——然后呢？学多少？怎么验证自己学会了？

这个工具的设计原则只有一条：**每一个输出都必须能被质疑和验证**。

## 核心功能

**看板一：岗位画像**
逆向拆解JD，提取企业真正的招聘刚需，五维雷达图可视化。

**看板二：匹配度分析（解密黑盒）**
显示加权计算公式和各维度得分明细表，让你知道72%是怎么算出来的。

**看板三：周级行动路线图**
每条建议绑定硬性KPI交付物（"完成15道SQL中等题"，不是"学习SQL"）。

## 技术架构

```
用户输入JD + 简历PDF
      ↓
PyPDF2 解析简历文本
      ↓
Prompt组装（Temperature=0.2锁定输出稳定性）
      ↓
DeepSeek API → 强制JSON结构输出
      ↓
Plotly雷达图 + 数据明细表 + KPI卡片渲染
```

异常处理：JSON解析失败时前端优雅降级，不闪退。

## 本地运行

```bash
git clone https://github.com/EllaYng/CareerLens
cd job-intel-station
pip install -r requirements.txt
cp .env.example .env   # 填入你的DeepSeek API Key
streamlit run app.py
```

## 产品截图

| 首页 | 岗位画像 | 匹配度分析 | 行动路线图 |
| ---- |---------|-----------|-----------|
| ![](docs/screenshots/00_home.jpg) | ![](docs/screenshots/01_job_profile.png) | ![](docs/screenshots/02_analysis.png) | ![](docs/screenshots/03_roadmap.png) |

## 作者

EllaYng 
[GitHub主页](https://github.com/EllaYng) | [产品PRD文档](docs/PRD_v2.0.md) | [查看完整截图](docs/screenshots/)