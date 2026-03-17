"""主评估脚本，运行所有评估模块并生成综合评估报告。"""

import json
import datetime
from examor_cli.evaluation.rag_evaluation import evaluate_rag
from examor_cli.evaluation.question_evaluation import evaluate_question_generation
from examor_cli.evaluation.agent_evaluation import evaluate_agent
from examor_cli.evaluation.system_evaluation import evaluate_system_reliability
from examor_cli.evaluation.auto_evaluation import evaluate_automation


def generate_evaluation_report():
    """生成综合评估报告。"""
    print("开始评估...")
    
    # 1. 评估 RAG 层
    print("\n1. 评估 RAG 层...")
    rag_results = evaluate_rag()
    
    # 2. 评估题目生成质量
    print("\n2. 评估题目生成质量...")
    question_results = evaluate_question_generation()
    
    # 3. 评估 Agent 决策能力
    print("\n3. 评估 Agent 决策能力...")
    agent_results = evaluate_agent()
    
    # 4. 评估整体系统可靠性
    print("\n4. 评估整体系统可靠性...")
    system_results = evaluate_system_reliability()
    
    # 5. 自动化评估
    print("\n5. 自动化评估...")
    auto_results = evaluate_automation()
    
    # 生成报告
    report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "rag_evaluation": rag_results,
        "question_evaluation": question_results,
        "agent_evaluation": agent_results,
        "system_evaluation": system_results,
        "auto_evaluation": auto_results
    }
    
    # 保存报告
    report_path = f"evaluation_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n评估报告已保存到: {report_path}")
    
    # 打印摘要
    print("\n评估摘要:")
    print(f"RAG 层 - Recall@3: {rag_results.get('Recall@3', 'N/A'):.4f}")
    print(f"RAG 层 - Precision@3: {rag_results.get('Precision@3', 'N/A'):.4f}")
    print(f"题目生成 - 平均格式有效率: {question_results.get('average_format_valid_rate', 'N/A'):.4f}")
    print(f"题目生成 - 平均 LLM 评分: {question_results.get('average_score', 'N/A'):.2f}")
    print(f"Agent 决策 - 平均工具调用准确性: {agent_results.get('average_tool_accuracy', 'N/A'):.4f}")
    print(f"Agent 决策 - 任务成功率: {agent_results.get('task_success_rate', 'N/A'):.4f}")
    print(f"系统可靠性 - End-to-End 任务成功率: {system_results.get('end_to_end', {}).get('success_rate', 'N/A'):.4f}")
    print(f"系统可靠性 - 平均执行时间: {system_results.get('end_to_end', {}).get('average_execution_time', 'N/A'):.4f} 秒")
    
    return report


if __name__ == "__main__":
    generate_evaluation_report()
