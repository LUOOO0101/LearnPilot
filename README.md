<samp>

<img src="https://img.shields.io/badge/Python-3.11-%23fff?style=flat-square&labelColor=7d09f1">

### 项目简介

`Examor-CLI` 是一个基于大模型的命令行出题 / 批改系统，支持：

- 从笔记文本中自动生成多种题型（单选题、简答题、填空题）并入库管理
- AI 批改主观题，返回分数和详细反馈
- PDF + RAG + Agent 模式：从 PDF 知识库检索并自适应生成考题
- 记忆用户历史答题表现（错题本、题目正确率），支持自适应出题

整个项目已经整理为标准 Python 包 `examor_cli`，既可以通过 CLI 使用，也可以在其他项目中通过 `import examor_cli` 复用核心能力。

### 技术栈概览

- **语言与运行环境**
  - Python 3.11
- **核心依赖**
  - `langchain-openai`：大模型调用（DeepSeek 兼容接口）
  - `langchain-community`、`langchain-text-splitters`：PDF 文档加载与文本切分
  - `FAISS`：向量检索构建 RAG 知识库
  - `pymysql`：MySQL 数据库访问
  - `click`：命令行 CLI 框架
  - `rich`：终端输出美化（表格、颜色、交互提示）
  - `python-dotenv`：环境变量管理（API Key、DB 配置等）
- **架构模块**
  - `examor_cli.config`：统一配置与环境变量
  - `examor_cli.core`：出题与批改核心逻辑
  - `examor_cli.db`：数据库访问（题库、答题记录、用户统计）
  - `examor_cli.rag`：PDFRAG，负责 PDF 知识库 + 向量检索
  - `examor_cli.agent`：`PDFExamAgent`，结合 RAG + LLM 的智能出题 Agent
  - `examor_cli.memory`：短期/长期记忆管理（用户画像、错题本）
  - `examor_cli.cli`：CLI 入口和各子命令

### 核心功能

- **考题生成**
  - 支持从任意笔记文本生成多种题型：`single_choice`、`short_answer`、`fill_blank`
  - 内置格式校验与 JSON 解析重试逻辑，保证大模型输出结构化答案
  - 自动生成单选题选项，并在 CLI 中友好展示

- **AI 批改**
  - 使用大模型对主观题进行批改，返回分数（0–100）和详细文字反馈
  - 对大模型返回的 Markdown / 代码块结果做清洗和容错解析

- **题库管理**
  - MySQL 持久化存储题目与答题记录
  - 初始化数据库结构、查询题库列表、分页/筛选题目
  - 支持一键清空题库：`clear-db` 命令（带二次确认）

- **RAG + PDF 知识库**
  - 通过 `PDFRAG` 从本地 PDF 构建向量检索库（FAISS）
  - 基于查询内容，从 PDF 知识库检索相关上下文，用于增强出题

- **Agent 模式出题**
  - `PDFExamAgent`：结合 RAG 检索结果 + 大模型分析
  - 自动分析难度、核心知识点、建议题目数量/题型
  - 基于知识库与分析结果生成题目，并写入题库

- **记忆（Memory）与自适应出题**
  - 短期记忆（`SessionMemory`）：
    - 记录本次会话中用户的题型/难度偏好
  - 长期记忆（数据库）：
    - `user_question_stats` 按题目维度记录：
      - `total_attempts` 总作答次数
      - `correct_attempts` 答对次数
      - `last_score`、`last_answer_at`
    - 定义“易错题”：作答次数 ≥ 3 且正确率 < 60%
  - 自适应出题：
    - CLI 普通出题和 Agent 出题时，会读取历史统计：
      - 按题型聚合，识别弱项题型
      - 根据“易错题”列表，将这些题目的摘要与正确率注入 Prompt，提示大模型：
        > 优先覆盖这些题的知识点，不要直接重复原题
    - 提供 `list-wrong` 命令查看“错题本”（按题目粒度展示）

### 面向秋招的核心亮点 / 创新点

- **1. 模块化可复用的 AI 出题 / 批改引擎**
  - 将所有大模型调用与业务逻辑拆入 `examor_cli.core`，暴露统一 API：
    - `generate_questions`、`generate_questions_with_format_check`、`evaluate_answer`
  - 其他服务可以直接 `import examor_cli` 复用核心出题/批改能力，CLI 只是其中一种前端。

- **2. 结合 RAG + Agent 的智能出题链路**
  - 从 PDF 文档构建向量检索库（FAISS），通过 RAG 获取高相关上下文
  - Agent 先分析难度、核心知识点、建议题型，再调用出题引擎生成题目
  - 整个链路是一个完整的小型“AI 考试出题 Agent”，展示了对 LangChain、RAG、LLM 协作的实际工程落地能力。

- **3. 按题目粒度的“错题本 + 自适应出题”**
  - 不只是统计“用户不擅长哪种题型”，而是为每一道题记录历史表现：
    - 总共做了几次、错了几次、正确率是多少
  - 在此基础上：
    - 定义统一的“易错题”规则
    - 提供 `list-wrong` 命令查看错题本
    - 在后续出题 Prompt 中注入易错题摘要，让大模型优先围绕这些知识点生成新题
  - 这是一个可以向面试官重点讲解的“基于用户行为的学习路径自适应”设计，即使在 CLI 项目中也实现了类似智能练习 App 的效果。

- **4. 稳定性与工程细节**
  - 对大模型返回的 JSON 做严格格式校验和重试，减少服务崩溃
  - 对批改结果中的 Markdown 代码块进行清洗，兼容模型输出习惯
  - CLI 中使用 `rich` 做了友好的交互体验（表格、确认提示等）
  - 提供一键清空题库命令（带二次确认），方便开发调试和测试重置

### 安装与运行

#### 安装依赖

```bash
pip install -r requirements.txt
```

配置环境变量（例如在 `.env` 中）：

```bash
EXAMOR_DB_HOST=localhost
EXAMOR_DB_PORT=52020
EXAMOR_DB_USER=root
EXAMOR_DB_PASSWORD=123456
EXAMOR_DB_NAME=examor

EXAMOR_LLM_API_KEY=your_deepseek_api_key
EXAMOR_LLM_BASE_URL=https://api.deepseek.com/v1
EXAMOR_LLM_MODEL=deepseek-chat
```

#### 初始化数据库

```bash
python -m examor_cli.cli.main init-db
```

#### 基础命令

- 生成考题（从笔记文本）：

```bash
python -m examor_cli.cli.main generate
```

- 根据题目 ID 答题并 AI 批改：

```bash
python -m examor_cli.cli.main answer --question-id 1
```

- 查看题库列表：

```bash
python -m examor_cli.cli.main list
```

- 分页/筛选题目：

```bash
python -m examor_cli.cli.main list-questions --page 1 --page-size 10 --type single_choice
```

- 查看“错题本”（易错题）：

```bash
python -m examor_cli.cli.main list-wrong
```

- 一键清空题库（危险操作，带确认）：

```bash
python -m examor_cli.cli.main clear-db
```

#### RAG + Agent 模式

- 构建 PDF 向量库：

```bash
python -m examor_cli.cli.main build-vector-db
```

- 基于 PDF 知识库 + Agent 自适应出题：

```bash
python -m examor_cli.cli.main rag-agent-generate-pdf
```

</samp>
