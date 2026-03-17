"""整体系统可靠性评估脚本，包括 End-to-End 任务成功率和人工评估。"""

import time
from typing import List, Dict
from examor_cli.agent.learning_agent import run_learning_agent


def create_system_test_cases() -> List[Dict[str, any]]:
    """创建系统测试用例。"""
    return [
        {
            "input": "我想了解我的学习情况并获取建议",
            "description": "获取用户画像和学习建议"
        },
        {
            "input": "根据 Python 字典的特性出 3 道题",
            "description": "根据知识点出题"
        },
        {
            "input": "查看我的错题本",
            "description": "查看易错题"
        },
        {
            "input": "我该如何提升我的 Python 编程能力",
            "description": "获取学习建议"
        },
        {
            "input": "根据 Python 列表的方法出 2 道题",
            "description": "根据知识点出题"
        }
    ]


def evaluate_end_to_end() -> Dict[str, any]:
    """评估 End-to-End 任务成功率。"""
    test_cases = create_system_test_cases()
    
    results = []
    total_success = 0
    total_time = 0
    
    for test_case in test_cases:
        user_input = test_case["input"]
        description = test_case["description"]
        
        # 记录开始时间
        start_time = time.time()
        
        # 运行 Agent
        try:
            response = run_learning_agent(user_input)
            success = True
        except Exception as e:
            response = str(e)
            success = False
        
        # 记录结束时间
        end_time = time.time()
        execution_time = end_time - start_time
        total_time += execution_time
        
        if success:
            total_success += 1
        
        results.append({
            "input": user_input,
            "description": description,
            "success": success,
            "execution_time": execution_time,
            "response": response[:200] + "..." if len(response) > 200 else response
        })
    
    # 计算结果
    success_rate = total_success / len(test_cases)
    avg_execution_time = total_time / len(test_cases)
    
    return {
        "results": results,
        "success_rate": success_rate,
        "average_execution_time": avg_execution_time
    }


def generate_manual_evaluation_form() -> str:
    """生成人工评估表单。"""
    form = """# 系统人工评估表单

## 评估维度

### 1. 功能完整性
- [ ] 能够正确响应所有测试用例
- [ ] 能够正确调用所需工具
- [ ] 能够生成正确的题目
- [ ] 能够提供有用的学习建议

### 2. 响应质量
- [ ] 回答准确无误
- [ ] 语言表达清晰
- [ ] 内容相关性高
- [ ] 建议实用性强

### 3. 系统稳定性
- [ ] 无崩溃或错误
- [ ] 响应时间合理
- [ ] 资源使用适度

### 4. 用户体验
- [ ] 交互流畅自然
- [ ] 反馈及时明确
- [ ] 界面友好易用

## 测试用例评估

"""
    
    test_cases = create_system_test_cases()
    for i, test_case in enumerate(test_cases, 1):
        form += f"### 用例 {i}: {test_case['description']}\n"
        form += f"输入: {test_case['input']}\n"
        form += "评价: [ ] 优秀 [ ] 良好 [ ] 一般 [ ] 差\n\n"
    
    return form


def evaluate_system_reliability() -> Dict[str, any]:
    """评估整体系统可靠性。"""
    # 评估 End-to-End 任务成功率
    end_to_end_results = evaluate_end_to_end()
    
    # 生成人工评估表单
    manual_evaluation_form = generate_manual_evaluation_form()
    
    return {
        "end_to_end": end_to_end_results,
        "manual_evaluation_form": manual_evaluation_form
    }


if __name__ == "__main__":
    results = evaluate_system_reliability()
    print("系统可靠性评估结果:")
    print(f"End-to-End 任务成功率: {results['end_to_end']['success_rate']:.4f}")
    print(f"平均执行时间: {results['end_to_end']['average_execution_time']:.4f} 秒")
    print("\n人工评估表单:")
    print(results['manual_evaluation_form'])
