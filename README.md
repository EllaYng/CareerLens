# 求职情报站

一个帮助求职者整合全网求职经验、生成结构化指南的 AI 工具。

## 产品背景

求职过程中，小红书、知乎等平台上有大量碎片化的求职经验，但信息分散、质量参差不齐，很难快速提炼出有用的内容。

求职情报站解决的核心问题：**把碎片化的求职信息，整理成结构化的求职指南。**

## 功能介绍

**模式一：自动搜索**
输入求职方向（如"AI产品经理"），系统自动搜索全网相关经验，整理成涵盖简历准备、面试技巧、常见问题、薪资谈判的结构化指南。

**模式二：链接总结**
粘贴若干图文链接，系统自动抓取内容，提炼核心观点，按主题分类整理输出。

## 技术栈

- **前端**：Streamlit
- **AI 模型**：DeepSeek V4 Flash API
- **搜索**：Tavily Search API
- **语言**：Python

## 本地运行

1. 克隆项目
```bash
git clone https://github.com/你的用户名/job-intel.git
cd job-intel
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置环境变量，新建 `.env` 文件：
```
TAVILY_API_KEY=你的key
DEEPSEEK_API_KEY=你的key
```

4. 启动应用
```bash
streamlit run app.py
```

## 作者

EllaYng | [GitHub](https://github.com/EllaYng)