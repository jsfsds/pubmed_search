#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PubMed 智能检索与导出工具

本模块为医学文献智能分析服务提供底层数据抓取、解析与导出能力。
"""

import os
import time
import hashlib
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Any
from Bio import Entrez
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class PubMedSearcher:
    """
    PubMed 检索与文章数据获取类，为智能分析服务提供底层数据支持。
    """
    def __init__(self, email: str, api_key: Optional[str] = None):
        """
        初始化 PubMed 检索器。
        参数：
            email: 用户邮箱（NCBI 要求）
            api_key: NCBI API Key（可选，提升限速）
        """
        self.email = email
        self.api_key = api_key or os.getenv('NCBI_API_KEY')
        Entrez.email = self.email
        if self.api_key:
            Entrez.api_key = self.api_key
        # 输出目录为项目根目录下的 output
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.output_dir = os.path.join(project_root, "output")
        os.makedirs(self.output_dir, exist_ok=True)

    def search(self, 
               advanced_search: str, 
               date_range: Optional[Tuple[str, str]] = None,
               max_results: int = 8,
               sort: Optional[str] = None,
               debug: bool = False) -> List[Dict[str, Any]]:
        """
        使用高级检索语法在 PubMed 上检索文献。
        参数：
            advanced_search: PubMed 检索语句
            date_range: (起始日期, 结束日期)，格式 YYYY/MM/DD
            max_results: 最大返回结果数
            sort: 排序方式
            debug: 是否打印调试信息
        返回：
            文章字典列表
        """
        search_term = advanced_search
        # 拼接日期范围
        if date_range:
            start_date, end_date = date_range
            date_filter = f" AND (\"{start_date}\"[Date - Publication] : \"{end_date}\"[Date - Publication])"
            search_term += date_filter
        try:
            if debug:
                print(f"检索 PubMed，查询: {search_term}, 最大数: {max_results}, 排序: {sort}")
            # 检索
            if sort:
                search_handle = Entrez.esearch(
                    db="pubmed", term=search_term, retmax=max_results,
                    sort=sort, usehistory="y"
                )
            else:
                search_handle = Entrez.esearch(
                    db="pubmed", term=search_term, retmax=max_results,
                    usehistory="y"
                )
            search_results = Entrez.read(search_handle)
            search_handle.close()
            webenv = search_results["WebEnv"]
            query_key = search_results["QueryKey"]
            count = int(search_results["Count"])
            if debug:
                print(f"共找到 {count} 条结果，最多返回 {max_results} 条")
            if count == 0:
                if debug:
                    print("未找到结果")
                return []
            articles = []
            # 分批获取，避免超时
            batch_size = 100
            for start in range(0, min(count, max_results), batch_size):
                to_fetch = min(batch_size, max_results - start)
                end = start + to_fetch
                if debug:
                    print(f"获取第 {start+1} 到 {end} 条记录")
                try:
                    fetch_handle = Entrez.efetch(
                        db="pubmed",
                        retstart=start,
                        retmax=to_fetch,
                        webenv=webenv,
                        query_key=query_key,
                        retmode="xml"
                    )
                    records = Entrez.read(fetch_handle)["PubmedArticle"]
                    fetch_handle.close()
                    for record in records:
                        try:
                            article = self._parse_pubmed_record(record)
                            articles.append(article)
                        except Exception as e:
                            if debug:
                                print(f"解析单条记录出错: {e}")
                            continue
                    time.sleep(1)  # 防止 NCBI 限流
                except Exception as e:
                    if debug:
                        print(f"获取第 {start+1} 到 {end} 批次出错: {str(e)}")
                    continue
            return articles
        except Exception as e:
            if debug:
                print(f"PubMed 检索出错: {str(e)}")
            return []

    def _parse_pubmed_record(self, record: Dict) -> Dict[str, Any]:
        """
        解析 PubMed 记录为结构化字典。
        参数：
            record: Entrez.read 返回的 PubMed 记录
        返回：
            结构化文章字典
        """
        article_data = {}
        try:
            # 获取 MedlineCitation 和 Article
            medline_citation = record.get("MedlineCitation", {})
            article = medline_citation.get("Article", {})
            # 标题
            article_data["title"] = article.get("ArticleTitle", "")
            # 作者（去重）
            authors = set()
            author_list = article.get("AuthorList", [])
            for author in author_list:
                if "LastName" in author and "ForeName" in author:
                    authors.add(f"{author['LastName']} {author['ForeName']}")
                elif "LastName" in author and "Initials" in author:
                    authors.add(f"{author['LastName']} {author['Initials']}")
                elif "LastName" in author:
                    authors.add(author["LastName"])
                elif "CollectiveName" in author:
                    authors.add(author["CollectiveName"])
            article_data["authors"] = list(authors)
            # 期刊
            journal = article.get("Journal", {})
            article_data["journal"] = journal.get("Title", "")
            # 发表日期
            pub_date = {}
            journal_issue = journal.get("JournalIssue", {})
            if "PubDate" in journal_issue:
                pub_date = journal_issue["PubDate"]
            pub_date_str = ""
            if "Year" in pub_date:
                pub_date_str = pub_date["Year"]
                if "Month" in pub_date:
                    pub_date_str += f" {pub_date['Month']}"
                    if "Day" in pub_date:
                        pub_date_str += f" {pub_date['Day']}"
            article_data["publication_date"] = pub_date_str
            # 摘要
            abstract_text = ""
            if "Abstract" in article and "AbstractText" in article["Abstract"]:
                abstract_parts = article["Abstract"]["AbstractText"]
                if isinstance(abstract_parts, list):
                    for part in abstract_parts:
                        if isinstance(part, str):
                            abstract_text += part + " "
                        elif isinstance(part, dict) and "#text" in part:
                            label = part.get("Label", "")
                            text = part["#text"]
                            if label:
                                abstract_text += f"{label}: {text} "
                            else:
                                abstract_text += text + " "
                else:
                    abstract_text = str(abstract_parts)
            article_data["abstract"] = abstract_text.strip()
            # 关键词（去重）
            keywords = set()
            mesh_headings = medline_citation.get("MeshHeadingList", [])
            for heading in mesh_headings:
                if "DescriptorName" in heading:
                    descriptor = heading["DescriptorName"]
                    if isinstance(descriptor, dict) and "content" in descriptor:
                        keywords.add(descriptor["content"])
                    elif isinstance(descriptor, str):
                        keywords.add(descriptor)
            keyword_lists = medline_citation.get("KeywordList", [])
            for keyword_list in keyword_lists:
                if isinstance(keyword_list, list):
                    for keyword in keyword_list:
                        if isinstance(keyword, str):
                            keywords.add(keyword)
                        elif isinstance(keyword, dict) and "content" in keyword:
                            keywords.add(keyword["content"])
            article_data["keywords"] = list(keywords)
            # PMID
            pmid = medline_citation.get("PMID", "")
            if isinstance(pmid, dict) and "content" in pmid:
                article_data["pmid"] = pmid["content"]
            else:
                article_data["pmid"] = str(pmid)
            # DOI
            doi = ""
            try:
                pubmed_data = record.get("PubmedData")
                if pubmed_data:
                    article_id_list = pubmed_data.get("ArticleIdList")
                    if article_id_list:
                        try:
                            for id_element in article_id_list:
                                if hasattr(id_element, 'attributes') and id_element.attributes.get('IdType') == 'doi':
                                    doi = str(id_element).strip()
                                    if doi: break
                                elif isinstance(id_element, dict) and id_element.get('IdType') == 'doi':
                                    doi = id_element.get('content', '').strip() or id_element.get('#text', '').strip()
                                    if doi: break
                        except TypeError:
                            if hasattr(article_id_list, 'attributes') and article_id_list.attributes.get('IdType') == 'doi':
                                doi = str(article_id_list).strip()
            except Exception as e:
                doi = ""
            article_data["doi"] = doi
        except Exception as e:
            # 单条解析异常保护
            article_data["parse_error"] = str(e)
        return article_data

    @staticmethod
    def _hash_query(query: str) -> str:
        """
        对检索式做 hash，便于输出文件命名唯一化。
        """
        return hashlib.sha1(query.encode("utf-8")).hexdigest()[:8]

    def export_to_txt(self, articles: List[Dict[str, Any]], query: Optional[str] = None, filename: Optional[str] = None) -> str:
        """
        导出文章到格式化文本文件。
        参数：
            articles: 文章字典列表
            query: 检索式（用于命名 hash）
            filename: 输出文件名（可选）
        返回：
            文件路径
        """
        if not filename:
            date_str = datetime.now().strftime("%Y%m%d")
            count = len(articles)
            query_hash = self._hash_query(query or "") if query else "noquery"
            filename = f"pubmed_{date_str}_{query_hash}_{count}articles.txt"
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            for i, article in enumerate(articles, 1):
                f.write(f"Article {i}\n")
                f.write("-" * 80 + "\n")
                f.write(f"Title: {article.get('title', '')}\n")
                f.write(f"Authors: {', '.join(article.get('authors', []))}\n")
                f.write(f"Journal: {article.get('journal', '')}\n")
                f.write(f"Publication Date: {article.get('publication_date', '')}\n")
                f.write(f"Abstract:\n{article.get('abstract', '')}\n")
                f.write(f"Keywords: {', '.join(article.get('keywords', []))}\n")
                f.write(f"PMID: {article.get('pmid', '')}\n")
                f.write(f"DOI: {article.get('doi', '')}\n")
                f.write("=" * 80 + "\n\n")
        print(f"已导出 {len(articles)} 篇文章到 {filepath}")
        return filepath
