"""RAG 层评估脚本，计算 Recall@k 和 Precision@k。"""

import json
from typing import List, Dict, Tuple
from examor_cli.rag import PDFRAG


def create_rag_test_dataset() -> List[Dict[str, any]]:
    """创建 RAG 测试数据集。"""
    return [
        {
            "query": "Python 字典的特性",
            "relevant_docs": ["字典的键必须是可哈希对象", "字典的值可以是任意类型"]
        },
        {
            "query": "Python 列表的方法",
            "relevant_docs": ["append() 方法添加元素", "extend() 方法扩展列表", "sort() 方法排序"]
        },
        {
            "query": "Python 函数定义",
            "relevant_docs": ["使用 def 关键字定义函数", "函数可以有参数和返回值"]
        },
        {
            "query": "Python 类的继承",
            "relevant_docs": ["使用 class 关键字定义类", "通过括号指定父类"]
        },
        {
            "query": "Python 文件操作",
            "relevant_docs": ["使用 open() 函数打开文件", "使用 with 语句自动关闭文件"]
        }
    ]


def calculate_recall_precision(
    retrieved_docs: List[str],
    relevant_docs: List[str],
    k: int
) -> Tuple[float, float]:
    """计算 Recall@k 和 Precision@k。"""
    retrieved_docs_k = retrieved_docs[:k]
    
    # 计算相关文档的数量
    relevant_retrieved = 0
    for doc in retrieved_docs_k:
        for relevant_doc in relevant_docs:
            if relevant_doc in doc:
                relevant_retrieved += 1
                break
    
    # 计算 Recall@k
    recall = relevant_retrieved / len(relevant_docs) if relevant_docs else 0.0
    
    # 计算 Precision@k
    precision = relevant_retrieved / k if k > 0 else 0.0
    
    return recall, precision


def evaluate_rag(k_values: List[int] = [1, 3, 5]) -> Dict[str, any]:
    """评估 RAG 检索效果。"""
    rag = PDFRAG()
    test_dataset = create_rag_test_dataset()
    
    results = {}
    for k in k_values:
        total_recall = 0.0
        total_precision = 0.0
        
        for item in test_dataset:
            query = item["query"]
            relevant_docs = item["relevant_docs"]
            
            # 执行检索
            retrieved_context = rag.retrieve(query, k=k)
            retrieved_docs = retrieved_context.split("\n\n")
            
            # 计算 Recall@k 和 Precision@k
            recall, precision = calculate_recall_precision(retrieved_docs, relevant_docs, k)
            total_recall += recall
            total_precision += precision
        
        # 计算平均值
        avg_recall = total_recall / len(test_dataset)
        avg_precision = total_precision / len(test_dataset)
        
        results[f"Recall@{k}"] = avg_recall
        results[f"Precision@{k}"] = avg_precision
    
    return results


if __name__ == "__main__":
    results = evaluate_rag()
    print("RAG 评估结果:")
    for metric, value in results.items():
        print(f"{metric}: {value:.4f}")
