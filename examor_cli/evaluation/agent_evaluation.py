"""Agent 决策能力评估脚本，包括 Tool Call Accuracy 和 Task Success Rate 评估。"""

from typing import List, Dict, Tuple
from examor_cli.agent.learning_agent import run_learning_agent


def create_agent_test_cases() -> List[Dict[str, any]]:
    """创建 Agent 测试用例。"""
    return [
        {
            "input": "我想了解我的学习情况",
            "expected_tools": ["get_user_profile_tool", "generate_learning_suggestions_tool"],
            "description": "获取用户画像和学习建议"
        },
        {
            "input": "根据 agent的特性出题",
            "expected_tools": ["get_user_profile_tool", "get_rag_context_tool", "generate_questions_tool", "save_generated_questions_to_db_tool"],
            "description": "根据知识点出题"
        },
        {
            "input": "查看我的错题本",
            "expected_tools": ["get_hard_questions_tool"],
            "description": "查看易错题"
        },
        {
            "input": "我该如何快速掌握agent开发能力",
            "expected_tools": ["get_user_profile_tool", "generate_learning_suggestions_tool"],
            "description": "获取学习建议"
        },
        {
            "input": "如何提升RAG的召回能力",
            "expected_tools": ["get_user_profile_tool", "get_rag_context_tool", "generate_questions_tool", "save_generated_questions_to_db_tool"],
            "description": "根据知识点出题"
        }
    ]


def extract_tool_calls(response: str) -> List[str]:
    """从 Agent 响应中提取工具调用。"""
    # 注意：这里需要根据实际的 Agent 输出格式进行调整
    # 由于当前的 run_learning_agent 函数返回的是最终回答，而不是工具调用过程
    # 这里我们假设 Agent 会在回答中提到使用了哪些工具
    # 实际实现中可能需要修改 run_learning_agent 函数，使其返回工具调用历史
    tool_names = ["get_user_profile_tool", "get_hard_questions_tool", "get_rag_context_tool", "generate_questions_tool", "save_generated_questions_to_db_tool", "generate_learning_suggestions_tool"]
    used_tools = []
    
    for tool_name in tool_names:
        if tool_name in response:
            used_tools.append(tool_name)
    
    return used_tools


def evaluate_tool_call_accuracy(used_tools: List[str], expected_tools: List[str]) -> float:
    """评估工具调用准确性。"""
    if not expected_tools:
        return 1.0 if not used_tools else 0.0
    
    # 计算精确率和召回率
    true_positives = len(set(used_tools) & set(expected_tools))
    precision = true_positives / len(used_tools) if used_tools else 0.0
    recall = true_positives / len(expected_tools) if expected_tools else 0.0
    
    # 计算 F1 分数
    if precision + recall == 0:
        return 0.0
    f1_score = 2 * (precision * recall) / (precision + recall)
    
    return f1_score


def evaluate_task_success(response: str, description: str) -> bool:
    """评估任务是否成功完成。"""
    # 简单的规则判断，实际应用中可能需要更复杂的逻辑
    success_indicators = {
        "获取用户画像和学习建议": ["用户画像", "学习建议"],
        "根据知识点出题": ["生成", "题目", "保存"],
        "查看易错题": ["易错题", "错题本"],
        "获取学习建议": ["学习建议", "提升"]
    }
    
    indicators = success_indicators.get(description, [])
    if not indicators:
        return True
    
    return all(indicator in response for indicator in indicators)


def evaluate_agent() -> Dict[str, any]:
    """评估 Agent 决策能力。"""
    test_cases = create_agent_test_cases()
    
    results = []
    total_tool_accuracy = 0.0
    total_task_success = 0
    
    for test_case in test_cases:
        user_input = test_case["input"]
        expected_tools = test_case["expected_tools"]
        description = test_case["description"]
        
        # 运行 Agent
        response = run_learning_agent(user_input)
        
        # 提取工具调用
        used_tools = extract_tool_calls(response)
        
        # 评估工具调用准确性
        tool_accuracy = evaluate_tool_call_accuracy(used_tools, expected_tools)
        total_tool_accuracy += tool_accuracy
        
        # 评估任务成功与否
        task_success = evaluate_task_success(response, description)
        if task_success:
            total_task_success += 1
        
        results.append({
            "input": user_input,
            "description": description,
            "expected_tools": expected_tools,
            "used_tools": used_tools,
            "tool_accuracy": tool_accuracy,
            "task_success": task_success,
            "response": response[:200] + "..." if len(response) > 200 else response
        })
    
    # 计算平均结果
    avg_tool_accuracy = total_tool_accuracy / len(test_cases)
    task_success_rate = total_task_success / len(test_cases)
    
    return {
        "results": results,
        "average_tool_accuracy": avg_tool_accuracy,
        "task_success_rate": task_success_rate
    }


if __name__ == "__main__":
    results = evaluate_agent()
    print("Agent 决策能力评估结果:")
    print(f"平均工具调用准确性: {results['average_tool_accuracy']:.4f}")
    print(f"任务成功率: {results['task_success_rate']:.4f}")
