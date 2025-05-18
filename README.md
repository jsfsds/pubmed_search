**PubMed_Search 是一个基于 模型上下文协议/MCP 构建的智能医学文献分析工具。它旨在帮助科研人员、医学从业者和学生快速检索 PubMed 数据库，并利用大型语言模型 (LLM) 的能力对文献摘要进行智能分析和总结**

**请注意**: 本项目目前仍有许多待完善的功能。欢迎任何形式的反馈和贡献，以帮助项目不断进步。


## 功能特性

- **PubMed 文献检索**: 通过关键词、作者、期刊等多种方式，使用 PubMed 高级检索语法进行文献检索。
- **智摘要总结**: 利用 SiliconFlow 用大型语言模型对检索到的多篇文献摘要进行综合概述。


## 可用工具

以下为当前可用的 MCP 工具及用法示例：

### 1. fetch_articles
**功能**: 使用 PubMed 高级检索语法获取文章，默认检索 2015/01/01 至今。
**参数**:
- `query` (str): PubMed 高级检索查询语句
- `email` (str, 可选): 用于 NCBI Entrez 的邮箱，默认为环境变量 `NCBI_EMAIL`
- `from_date` (str, 可选): 查询开始日期（YYYY/MM/DD），默认为 2015/01/01
- `to_date` (str, 可选): 查询结束日期（YYYY/MM/DD），默认为当天
- `limit` (int, 可选): 最大返回文章数，默认为 8
- `order_by` (str, 可选): 排序方式
- `output` (str, 可选): 输出文件名（.txt）
**返回**:
```json
{"success": true, "status": "fetch_completed", "message": "…", "result_file": "…", "article_count": n}
```
+**状态说明**:
+- `fetch_completed`: 检索成功并已保存结果文件。
+- `fetch_failed`: 检索失败，可能由于缺少邮箱或检索过程出错。
+- `no_results`: 检索成功但未找到任何结果。
+- `save_failed`: 结果文件保存失败，请检查路径和权限。


### 2. summarize_abstracts
**功能**: 对指定结果文件中的摘要进行综合概述
**参数**:
- `filenames` (List[str]): 要汇总的文件名列表
- `model` (str): 模型名，默认为 deepseek-ai/DeepSeek-V3
- `max_tokens` (int): 最大 tokens，默认为 512
- `temperature` (float): 温度，默认为 0.3
**返回**:
```json
{"success": true, "status": "summary_completed", "summary": "…"}
```
+**状态说明**:
+- `summary_completed`: 摘要汇总成功。
+- `missing_files`: 指定的结果文件未找到。
+- `extract_failed`: 未能提取到摘要内容。
+- `summary_failed`: 汇总过程中调用 API 或处理失败。


### 3. format_citations
**功能**: 将指定结果文件中的文章信息格式化为引用字符串列表。
**参数**:
- `filenames` (List[str]): 要格式化的文件名列表
**返回**:
```json
{"success": true, "status": "citations_formatted", "citations": ["…", "..."]}
```
+**状态说明**:
+- `citations_formatted`: 引用格式化成功。
+- `format_failed`: 格式化失败，可能由于指定文件未找到或读取错误。


## 安装与配置

### 1. 环境准备
- Python 3.8 或更高版本
- Git

### 2. 克隆项目
```bash
git clone <您的项目仓库地址>
cd pubmed_search_2
```

### 3. 创建并激活虚拟环境 (推荐)
```bash
python -m venv .venv
# Windows
.venv\\Scripts\\activate
# macOS/Linux
source .venv/bin/activate
```

### 4. 安装依赖
```bash
pip install -r requirements.txt
```

### 5. 配置环境变量
项目需要以下环境变量来正常工作。请在项目根目录下创建一个 `.env` 文件 (可以复制 `.env.example` 并重命名)，并填入您的配置信息：

```env
NCBI_EMAIL="your_email@example.com" # 用于 PubMed Entrez API 的邮箱地址
NCBI_API_KEY="your_ncbi_api_key" # (可选) 用于 PubMed Entrez API 的 API Key，不填则使用匿名模式，可能会有速率限制
SILICONFLOW_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" # 用于 SiliconFlow 摘要总结服务的 API Key
```


## 使用示例 （Cursor）

确保您已经在 Cursor 的 `mcp.json` 文件中配置了此服务。根据您提供的信息，配置示例如下：

```json
{
  "PubMed": {
    "command": "cmd",
    "args": [
      "/c",
      "path/to/python.exe",
      "path/to/mcp_pubmed_service/main.py"
    ]
  }
}
```

## 致谢

本项目的核心功能和部分代码实现基于 [Darkroaster/pubmearch](https://github.com/Darkroaster/pubmearch) 项目 (作者：姜宇)。
我们对原作者的开源贡献表示衷心的感谢！本项目遵循原项目的 MIT 许可证。
