<div align="center">
  <img src="images/logo/banner.png" alt="DataGenFlow Logo"/>
  <p>
    <a href="#快速开始">快速开始</a> •
    <a href="#工作原理">工作原理</a> •
    <a href="#文档">文档</a>
  </p>

  [![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
  [![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
  [![GitHub stars](https://img.shields.io/github/stars/nicofretti/DataGenFlow.svg?style=social&label=Star)](https://github.com/nicofretti/DataGenFlow)
</div>

<div align="center">

https://github.com/user-attachments/assets/7ca7a319-e2c1-4e24-a4c7-2b098d692aa1

**定义种子 → 构建流程 → 审查结果 → 导出数据**

[观看完整演示](images/video/full_video.mp4)

</div>

## 为什么选择 DataGenFlow 🌱

DataGenFlow 将复杂的数据生成工作流转变为直观的可视化流程。这是一个极简工具，帮助你通过种子模板生成和验证数据，并提供完整的可见性。

### 核心优势

- 易于扩展：分钟级添加自定义模块，自动发现
- 快速开发：可视化流程构建器消除样板代码
- 简单易用：直观的拖放界面，无需培训
- 完全透明：完整的执行追踪，便于调试

## 快速开始

2分钟内即可开始使用：

```bash
# 安装依赖
make setup
make dev

# 启动应用（后端 + 前端）
make run-dev

# 打开 http://localhost:8000
```

**就是这样！**无需复杂配置，无需外部依赖。

## 工作原理

### TL;DR - 可视化概览

基于种子数据生成文本的简单流程示例：
```
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. 种子数据 (JSON)                                                      │
│    { "repetitions": 2, "metadata": {"topic": "AI", "level": "basic"} }  │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 2. 流程 (可视化拖放)                                                     │
│                                                                         │
│    ┌──────────────┐      ┌──────────────┐      ┌──────────────┐         │
│    │  LLM 模块    │ ───► │  验证器模块  │ ───► │  输出模块    │         │
│    │              │      │              │      │              │         │
│    └──────────────┘      └──────────────┘      └──────────────┘         │
│                                                                         │
│    累积状态流：                                                          │
│    topic, level  ─►  + assistant  ─►  + is_valid  ─►  + formatted       │
│                                                                         │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 3. 生成与审查                                                           │
│    + 为每个种子执行流程 × 重复次数                                        │
│    + 使用键盘快捷键审查结果 (A/R/E)                                       │
│    + 查看完整执行追踪以进行调试                                          │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 4. 导出                                                                 │
│    下载为 JSONL ─► 可用于训练/集成                                       │
└─────────────────────────────────────────────────────────────────────────┘
```

**核心概念：**每个模块将数据添加到**累积状态**，因此后续模块自动访问所有先前的输出——无需手动连接！

---

### 1. 定义种子数据

首先创建一个包含流程将使用的变量的 JSON 种子文件。种子定义了你想要生成的数据。

单个种子：
```json
{
  "repetitions": 2,
  "metadata": {
    "topic": "Python 编程",
    "difficulty": "初级"
  }
}
```

多个种子（生成不同的变体）：
```json
[
  {
    "repetitions": 1,
    "metadata": {
      "topic": "Python 列表",
      "difficulty": "初级"
    }
  },
  {
    "repetitions": 1,
    "metadata": {
      "topic": "Python 字典",
      "difficulty": "中级"
    }
  }
]
```

字段：
- `repetitions`: 使用此种子运行流程的次数
- `metadata`: 可通过 `{{ variable_name }}` 在模块中访问的变量

### 2. 可视化构建流程

使用拖放模块设计数据生成工作流。每个模块处理数据并将其传递给下一个模块。

#### 内置模块

从即用型模块开始：
- LLM 生成器：使用 AI 模型生成文本（OpenAI、Ollama 等）
- 验证器：检查质量（长度、禁用词、模式）
- JSON 验证器：确保结构化数据的正确性
- 输出格式化器：为审查页面格式化结果
- ... 更多即将推出！

#### 对话式 AI 垂直领域

DataGenFlow 包含基于研究的合成对话生成算法：

- **角色驱动对话** - 生成具有一致角色声音的真实多轮对话
- **反向翻译多样性** - 自动创建多样化变体，同时保持意图
- **对抗性扰动** - 生成边缘案例和鲁棒性测试场景
- **质量指标** - 自动计算多样性、连贯性和参与度评分

非常适合训练对话式 AI、聊天机器人和对话系统。使用预配置的"客户服务对话"模板即可开始。

📚 完整指南：[对话式 AI 垂直领域](docs/conversational-ai-vertical.md) | [研究算法](docs/research-algorithms.md)

#### 使用自定义模块扩展

DataGenFlow 的真正威力在于创建自己的模块。分钟级添加特定领域逻辑，自动发现：

```python
from lib.blocks.base import BaseBlock
from typing import Any

class SentimentAnalyzerBlock(BaseBlock):
    name = "情感分析器"
    description = "分析文本情感"
    inputs = ["text"]  # 此模块需要从累积状态获取的内容
    outputs = ["sentiment", "confidence"]  # 它添加到累积状态的内容

    async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        text = data["text"]  # 从累积状态访问
        sentiment = analyze_sentiment(text)

        # 返回值自动添加到累积状态
        return {
            "sentiment": sentiment.label,
            "confidence": sentiment.score
        }
```

将文件放入 `user_blocks/` 目录，重启后自动发现——无需配置。

为什么这很重要：
- 立即适应特定领域或工作流
- 集成专有验证逻辑或数据源
- 为团队构建可重用组件
- 以 Python 文件形式共享模块——就像复制/粘贴一样简单

**调试自定义模块**

需要调试自定义模块？使用附带的 `debug_pipeline.py` 脚本配合 VS Code 调试器。详见[开发者文档](DEVELOPERS.md#debugging-custom-blocks)。

📚 完整指南：[自定义模块开发](docs/how_to_create_blocks.md)

#### 累积状态

数据在流程中自动流动。每个模块将其输出添加到累积状态，后续每个模块都可以访问——无需手动连接：

```
    ┌─────────────────┐
    │   LLM 模块      │ → 输出: {"assistant": "生成的文本"}
    └─────────────────┘
        │
        ▼ (状态: assistant)
    ┌─────────────────┐
    │   验证器模块    │ → 输出: {"is_valid": true}
    └─────────────────┘
        │
        ▼ (状态: assistant, is_valid)
    ┌─────────────────┐
    │   输出模块      │ ← 可以访问两者: assistant, is_valid
    └─────────────────┘
```

这使得构建复杂流程变得极其简单——连接模块，它们自动共享数据。

### 3. 审查和优化

使用键盘快捷键（接受：A，拒绝：R，编辑：E）审查结果，并通过完整的执行追踪查看每个结果的生成过程。

### 4. 导出数据

以 JSONL 格式导出数据，按状态（已接受、已拒绝、待处理）筛选。

## 配置

创建 `.env` 文件（或从 `.env.example` 复制）：

```bash
# LLM 配置
LLM_ENDPOINT=http://localhost:11434/v1  # Ollama、OpenAI 等
LLM_API_KEY=                            # 某些端点可选
LLM_MODEL=llama3.2

# 数据库
DATABASE_PATH=data/qa_records.db

# 服务器
HOST=0.0.0.0
PORT=8000

# 调试模式（可选）
DEBUG=false  # 设置为 true 以获取详细日志
```

## 文档

📖 综合指南
- [如何使用 DataGenFlow](docs/how_to_use.md) - 完整用户指南
- [自定义模块开发](docs/how_to_create_blocks.md) - 扩展功能
- [开发者文档](DEVELOPERS.md) - 开发者技术参考

## 贡献

欢迎并感谢贡献。提交贡献前，请查看以下指南。

前提条件：
- 仔细阅读[贡献指南](CONTRIBUTING.md)
- 检查现有的 issue 和 pull request 以避免重复
- 遵循项目的提交约定和代码风格标准

贡献领域：
- 新的处理模块和流程模板
- 文档改进和示例
- Bug 修复和性能优化
- 测试覆盖率扩展
- 集成示例和用例

有关详细的技术要求和开发设置，请参阅[开发者文档](DEVELOPERS.md)。

## 设计策略

DataGenFlow 基于 **KISS 原则**（Keep It Simple, Stupid，保持简单）构建：

- 最小抽象：直接、易懂的代码胜过巧妙的技巧
- 扁平架构：简单结构胜过深层嵌套
- 显式设计：清晰的意图胜过隐式的魔法
- 组合优先：组合简单部分胜过复杂继承
- 开发者友好：易于理解、修改和扩展

结果：简单、易懂的代码，易于维护和扩展。

---

<div align="center">

[开始使用](#快速开始) • [查看文档](#文档)

祝数据生成愉快！🌱

</div>
