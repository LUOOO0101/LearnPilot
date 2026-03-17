"""题目生成质量评估脚本，包括规则校验和 LLM-as-Judge 评分。"""

import json
from typing import List, Dict
from langchain_openai import ChatOpenAI
from examor_cli.config import LLM_CONFIG
from examor_cli.core import generate_questions_with_format_check


llm = ChatOpenAI(
    api_key=LLM_CONFIG["api_key"],
    base_url=LLM_CONFIG["base_url"],
    model_name=LLM_CONFIG["model"],
    temperature=0.3,
)


def validate_question_format(question: Dict) -> bool:
    """校验题目格式是否正确。"""
    # 检查必要字段
    if not all(k in question for k in ["content", "type", "answer"]):
        return False
    
    # 检查单选题是否有选项
    if question["type"] == "single_choice" and "options" not in question:
        return False
    
    # 检查选项格式
    if question["type"] == "single_choice":
        options = question["options"]
        if not isinstance(options, dict):
            return False
        if len(options) < 2:
            return False
    
    return True


def generate_llm_judge_prompt(question: Dict, context: str) -> str:
    """生成 LLM-as-Judge 评分提示。"""
    return f"""
请作为教育专家，对以下生成的题目进行评分，满分 10 分。评分标准：
1. 相关性：题目是否与给定上下文相关（3分）
2. 准确性：题目内容是否准确，答案是否正确（3分）
3. 清晰度：题目表述是否清晰，易于理解（2分）
4. 难度适中：题目难度是否适中，既不过于简单也不过于困难（2分）

上下文：
{context}

题目：
{json.dumps(question, ensure_ascii=False, indent=2)}

请直接输出评分，格式为："评分：X"，其中 X 是 0-10 的整数。
"""


def evaluate_question_quality(questions: List[Dict], context: str) -> Dict[str, any]:
    """评估题目生成质量。"""
    # 规则校验
    format_valid = 0
    for question in questions:
        if validate_question_format(question):
            format_valid += 1
    format_valid_rate = format_valid / len(questions) if questions else 0.0
    
    # LLM-as-Judge 评分
    total_score = 0
    for question in questions:
        prompt = generate_llm_judge_prompt(question, context)
        response = llm.invoke(prompt)
        try:
            score = int(response.content.strip().split("：")[-1])
            total_score += score
        except:
            total_score += 0
    avg_score = total_score / len(questions) if questions else 0.0
    
    # 内容质量评估
    content_quality = {
        "format_valid_rate": format_valid_rate,
        "avg_score": avg_score,
        "total_questions": len(questions)
    }
    
    return content_quality


def evaluate_question_generation() -> Dict[str, any]:
    """评估题目生成整体质量。"""
    # 测试用例
    test_contexts = [
        "Python 字典是一种可变的映射类型，用于存储键值对。字典的键必须是可哈希（不可变）对象，如字符串、数字或元组。字典的值可以是任意数据类型，包括列表、字典等可变对象。同一个字典中，键必须唯一，但值可以重复。",
        "Python 列表是一种有序的可变序列，用于存储多个元素。常用的列表方法包括 append()（添加元素到末尾）、extend()（扩展列表）、insert()（插入元素）、remove()（移除元素）、pop()（弹出元素）、sort()（排序）和 reverse()（反转）。",
        "Python 函数使用 def 关键字定义，后跟函数名和括号中的参数列表。函数可以有返回值，使用 return 语句返回。函数参数可以有默认值，也可以使用 *args 和 **kwargs 处理可变参数。"
    ]
    
    results = []
    for context in test_contexts:
        try:
            questions = generate_questions_with_format_check(
                note_content=context,
                num=3,
                question_types=["single_choice", "short_answer"]
            )
            quality = evaluate_question_quality(questions, context)
            results.append(quality)
        except Exception as e:
            results.append({"error": str(e)})
    
    # 计算平均结果
    avg_format_valid_rate = 0
    avg_score = 0
    valid_results = [r for r in results if "error" not in r]
    
    if valid_results:
        avg_format_valid_rate = sum(r["format_valid_rate"] for r in valid_results) / len(valid_results)
        avg_score = sum(r["avg_score"] for r in valid_results) / len(valid_results)
    
    return {
        "results": results,
        "average_format_valid_rate": avg_format_valid_rate,
        "average_score": avg_score,
        "success_rate": len(valid_results) / len(results)
    }


if __name__ == "__main__":
    results = evaluate_question_generation()
    print("题目生成质量评估结果:")
    print(f"平均格式有效率: {results['average_format_valid_rate']:.4f}")
    print(f"平均 LLM 评分: {results['average_score']:.2f}")
    print(f"生成成功率: {results['success_rate']:.4f}")
