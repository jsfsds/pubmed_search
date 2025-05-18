import re
from typing import List, Optional

def extract_abstracts_from_file(filepath: str) -> Optional[str]:
    """
    从单个结果文件中提取 Abstract 部分（不含标题/作者等）。
    """
    text = open(filepath, encoding='utf-8').read()
    # 找到"Abstract:"到下一个"Keywords:"之间的内容（跨行匹配）
    m = re.search(r"Abstract:\s*(.+?)\s*Keywords:", text, flags=re.S)
    if not m:
        return None
    # 去掉多余空白
    return m.group(1).strip()

def extract_abstracts(filepaths: List[str]) -> str:
    """
    将多篇文章的摘要按段合并，用于下游 LLM 汇总。
    """
    abstracts = []
    for fp in filepaths:
        abs_txt = extract_abstracts_from_file(fp)
        if abs_txt:
            abstracts.append(abs_txt)
    return "\n\n".join(abstracts)
