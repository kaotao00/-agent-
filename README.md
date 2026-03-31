# 建筑工程智能标书平台

这是一个基础功能可演示讲解的建筑工程智能标书生成系统，包含：

- 多 Agent 协作编排
- 企业知识库与 RAG 检索
- 本地混合检索：关键词 + 伪向量 + rerank
- 可选 LangChain + Milvus 集成
- 可选通义千问生成
- FastAPI 后端
- 全中文前端页面
- PDF / Word / Excel / CSV / TXT / MD 混合导入

## 项目结构

- `main.py`: CLI demo entry
- `start_server.py`: FastAPI server entry
- `tender_system/`: backend domain logic
- `frontend/`: 中文演示页面
- `data/enterprise_docs.json`: 企业知识库

## 快速运行

### 1）运行命令行 Demo

```bash
python main.py
```

输出写入 `output/generated_tender.json`。

### 2）启动网页服务

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the API server:

```bash
python start_server.py
```

打开 `http://127.0.0.1:8000`。

## 可选：通义千问模式

Set environment variables before running:

```bash
set TENDER_USE_QWEN=1
set DASHSCOPE_API_KEY=your_api_key
set TENDER_QWEN_MODEL=qwen-plus
```

项目使用 DashScope 的 OpenAI 兼容接口。如果 Key 无效或 SDK 不可用，系统会自动回退到模板生成。

## 文档导入与 RAG 增量更新

你可以直接把企业 PDF、Word、Excel 等资料导入知识库，系统会自动抽取文本、切块并刷新检索索引。

接口示例：

```bash
curl -X POST "http://127.0.0.1:8000/api/ingest-document" \
  -F "file=@your_doc.pdf" \
  -F "category=technical" \
  -F "region=江苏" \
  -F "project_type=industrial" \
  -F "tags=pdf,施工组织,企业资料"
```

导入后的文本会：

- 自动切分为多个知识片段
- 追加写入 `data/enterprise_docs.json`
- 立即可被 `/api/search` 和 `/api/generate` 使用

支持格式：`.pdf`、`.docx`、`.xlsx`、`.csv`、`.txt`、`.md`

## 可选：LangChain + Milvus 模式

Set environment variables before starting the service:

```bash
set TENDER_USE_LANGCHAIN=1
set TENDER_USE_MILVUS=1
set TENDER_MILVUS_URI=http://localhost:19530
```

如果依赖或 Milvus 服务不可用，系统会自动回退到本地混合检索。

## 核心能力

- 项目经理 Agent 负责任务编排
- 技术、预算、商务、合规 Agent 分工生成
- 共享记忆统一工期、资质、报价等关键字段
- 合规规则校验模块间一致性
- 预算工具模拟企业定额计价系统
- 前端支持文档上传、知识导入、检索、生成全流程演示
