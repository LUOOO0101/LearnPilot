"""集成 Ragas 和 DeepEval 的自动化评估脚本。"""

import json
from typing import List, Dict
from examor_cli.rag import PDFRAG
from examor_cli.core import generate_questions_with_format_check


def evaluate_with_ragas():
    """使用 Ragas 进行评估。"""
    try:
        from ragas import evaluate
        from ragas.metrics import (context_precision, context_recall, context_relevancy, faithfulness)
        from datasets import Dataset
        
        # 创建测试数据集
        rag = PDFRAG()
        test_cases = [
            {
                "question": "Python 字典的特性",
                "ground_truth": "Python 字典的键必须是可哈希对象，值可以是任意类型",
                "contexts": [rag.retrieve("Python 字典的特性", k=3)]
            },
            {
                "question": "Python 列表的方法",
                "ground_truth": "Python 列表常用方法包括 append()、extend()、sort() 等",
                "contexts": [rag.retrieve("Python 列表的方法", k=3)]
            }
        ]
        
        # 转换为 Ragas 所需的数据集格式
        dataset = Dataset.from_list(test_cases)
        
        # 评估
        result = evaluate(
            dataset=dataset,
            metrics=[context_precision, context_recall, context_relevancy, faithfulness]
        )
        
        return result
    except ImportError:
        return "Ragas 未安装，请运行 'pip install ragas'"
    except Exception as e:
        return f"Ragas 评估失败: {str(e)}"

def evaluate_with_deepeval():
    """使用 DeepEval 进行评估。"""
    try:
        from deepeval import evaluate
        from deepeval.metrics import (AnswerRelevancyMetric, FaithfulnessMetric, ContextualRelevancyMetric)
        from deepeval.dataset import EvaluationDataset
        
        # 创建测试数据集
        rag = PDFRAG()
        test_cases = [
            {
                "input": "Python 字典的特性",
                "expected_output": "Python 字典的键必须是可哈希对象，值可以是任意类型",
                "actual_output": rag.retrieve("Python 字典的特性", k=3)
            },
            {
                "input": "Python 列表的方法",
                "expected_output": "Python 列表常用方法包括 append()、extend()、sort() 等",
                "actual_output": rag.retrieve("Python 列表的方法", k=3)
            }
        ]
        
        # 转换为 DeepEval 所需的数据集格式
        dataset = EvaluationDataset(test_cases)
        
        # 评估
        result = evaluate(
            dataset=dataset,
            metrics=[AnswerRelevancyMetric(), FaithfulnessMetric(), ContextualRelevancyMetric()]
        )
        
        return result
    except ImportError:
        return "DeepEval 未安装，请运行 'pip install deepeval'"
    except Exception as e:
        return f"DeepEval 评估失败: {str(e)}"


def evaluate_automation():
    """自动化评估主函数。"""
    results = {
        "ragas": evaluate_with_ragas(),
        "deepeval": evaluate_with_deepeval()
    }
    
    return results


if __name__ == "__main__":
    results = evaluate_automation()
    print("自动化评估结果:")
    print("Ragas 评估:")
    print(results["ragas"])
    print("\nDeepEval 评估:")
    print(results["deepeval"])
