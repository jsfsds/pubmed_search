#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
医学文献智能分析服务主程序

本模块实现了一个基于 MCP 协议的智能医学文献分析服务，支持 PubMed 检索、摘要汇总、引用格式化。
"""

import os
import sys
import logging
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from datetime import datetime

# 获取项目根目录，确保本地模块导入正确
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

# 导入依赖模块
import requests  # 用于调用 SiliconFlow API
from mcp_pubmed_service.summary import extract_abstracts
from mcp_pubmed_service.fetcher import PubMedSearcher
from mcp.server.fastmcp import FastMCP
from pythonjsonlogger import jsonlogger

# 配置结构化日志（JSON 格式），支持多进程安全
formatter = jsonlogger.JsonFormatter('%(asctime)s %(name)s %(levelname)s %(message)s %(module)s %(funcName)s %(lineno)d')
file_handler = logging.FileHandler(os.path.join(parent_dir, "insight.log"))
file_handler.setFormatter(formatter)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger = logging.getLogger("pubmed-mcp-server")
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# 输出目录
output_dir = os.path.join(parent_dir, "output")
os.makedirs(output_dir, exist_ok=True)
logger.info(f"输出目录: {output_dir}")

# 初始化 MCP 服务器
mcp_server = FastMCP(
    "PubMed Analyzer",
    description="用于分析 PubMed 检索结果的 MCP 服务器"
)

# 加载 .env 配置
load_dotenv()
DEFAULT_EMAIL = os.getenv("NCBI_EMAIL")
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY")

@mcp_server.tool(name="fetch_articles", description="使用 PubMed 高级检索语法获取文章")
def fetch_articles(
    query: str,
    email: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = 8,
    order_by: Optional[str] = None,
    output: Optional[str] = None
) -> Dict[str, Any]:
    """
    使用 PubMed 高级检索语法获取文章，支持日期范围、排序、定制输出名。
    """
    email = email or DEFAULT_EMAIL
    if not email:
        return {"success": False, "status": "fetch_failed", "error": "缺少邮箱，请在 .env 中设置 NCBI_EMAIL 或传入 email 参数"}
    try:
        logger.info(f"开始 PubMed 检索，查询: {query}，邮箱: {email}")
        searcher = PubMedSearcher(email)
        today_str = datetime.now().strftime("%Y/%m/%d")
        start = from_date or "2015/01/01"
        end = to_date or today_str
        # 检索并获取文章
        records = searcher.search(advanced_search=query, date_range=(start, end), max_results=limit, sort=order_by)
        if not records:
            logger.warning("未检索到任何结果")
            return {"success": False, "status": "no_results", "error": "未检索到任何结果。"}
        # 生成输出文件名，支持自定义或自动命名
        output_file = output or None
        output_path = searcher.export_to_txt(records, query=query, filename=output_file)
        if not os.path.exists(output_path):
            logger.error(f"结果文件创建失败: {output_path}")
            return {"success": False, "status": "save_failed", "error": f"结果文件保存失败，路径 {output_path} 不存在。"}
        logger.info(f"成功保存 {len(records)} 篇文章到 {output_path}")
        copied_path = os.path.join(output_dir, os.path.basename(output_path))
        if output_path != copied_path:
            import shutil; shutil.copy2(output_path, copied_path); logger.info(f"结果文件已复制到: {copied_path}")
        return {"success": True, "status": "fetch_completed", "message": f"检索成功，共找到 {len(records)} 篇文章。", "result_file": os.path.basename(output_path), "article_count": len(records)}
    except Exception as e:
        logger.error(f"fetch_articles 错误: {str(e)}", exc_info=True)
        return {"success": False, "status": "fetch_failed", "error": f"检索过程中出错: {str(e)}"}

@mcp_server.tool()
def summarize_abstracts(
    filenames: List[str],
    model: str = "deepseek-ai/DeepSeek-V3",
    max_tokens: int = 512,
    temperature: float = 0.3
) -> Dict[str, Any]:
    """
    读取 results/ 目录下指定文件的摘要，调用 SilconFlow DeepSeek-V3 模型生成总结。
    """
    # 拼接结果文件的绝对路径并检查文件存在
    filepaths = [os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "output", fn))
                 for fn in filenames]
    missing = [fp for fp in filepaths if not os.path.exists(fp)]
    if missing:
        return {"success": False, "status": "missing_files", "error": f"未找到文件: {missing}"}

    # 提取所有摘要文本
    raw_text = extract_abstracts(filepaths).strip()
    if not raw_text:
        debug_info = {}
        try:
            content = open(filepaths[0], encoding='utf-8').read()
            debug_info["has_abstract"] = "Abstract:" in content
            debug_info["has_keywords"] = "Keywords:" in content
            if debug_info["has_abstract"]:
                idx = content.find("Abstract:")
                debug_info["abstract_snippet"] = content[idx:idx+200]
            else:
                debug_info["prefix"] = content[:200]
        except Exception as e:
            debug_info["error_reading"] = str(e)
        return {
            "success": False,
            "status": "extract_failed",
            "error": "未能提取到任何摘要内容",
            "debug": debug_info
        }

    # 构造 SiliconFlow API 请求
    url = "https://api.siliconflow.cn/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "你是医学文献摘要助手，请对以下多篇文章摘要做简明扼要的综合概述："
            },
            {
                "role": "user",
                "content": raw_text
            }
        ],
        "stream": False,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": 0.7,
        "top_k": 50,
        "frequency_penalty": 0.0,
        "n": 1,
        "response_format": {"type": "text"}
    }

    # 发起 HTTP 调用
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        summary = data["choices"][0]["message"]["content"].strip()
        return {"success": True, "status": "summary_completed", "summary": summary}
    except Exception as e:
        return {"success": False, "status": "summary_failed", "error": str(e)}

@mcp_server.tool()
def format_citations(
    filenames: List[str]
) -> Dict[str, Any]:
    """
    格式化引用列表工具，将指定结果文件中的文章信息格式化为引用字符串列表。
    """
    citations = []
    # 遍历每个结果文件
    for fn in filenames:
        path = os.path.normpath(os.path.join(parent_dir, "output", fn))
        if not os.path.exists(path):
            return {"success": False, "status": "format_failed", "error": f"未找到文件: {fn}"}
        content = open(path, encoding="utf-8").read()
        # 按 Article 划分每篇文章块
        blocks = [b for b in content.split("Article ") if b.strip()]
        for block in blocks:
            lines = block.splitlines()
            title = authors = journal = pub_date = doi = pmid = ""
            for line in lines:
                if line.startswith("Title:"):
                    title = line.replace("Title:", "").strip()
                elif line.startswith("Authors:"):
                    authors = line.replace("Authors:", "").strip()
                elif line.startswith("Journal:"):
                    journal = line.replace("Journal:", "").strip()
                elif line.startswith("Publication Date:"):
                    pub_date = line.replace("Publication Date:", "").strip()
                elif line.startswith("DOI:"):
                    doi = line.replace("DOI:", "").strip()
                elif line.startswith("PMID:"):
                    pmid = line.replace("PMID:", "").strip()
            # 构造引用格式：作者 (年). 标题. 期刊. DOI; PMID
            year = pub_date.split()[0] if pub_date else ""
            cit = f"{authors} ({year}). {title}. {journal}. DOI:{doi}; PMID:{pmid}"
            citations.append(cit)
    return {"success": True, "status": "citations_formatted", "citations": citations}

def main():
    """启动 PubMed MCP 服务器。"""
    try:
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"已验证输出目录: {output_dir}")
        logger.info("启动 PubMed MCP 服务器")
        # 启动 MCP 服务器，使用 SSE transport 在HTTP端口监听
        mcp_server.run()
    except Exception as e:
        logger.critical(f"服务器启动失败: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()