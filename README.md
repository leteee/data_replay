# Data Replay Framework

这是一个模块化、可配置的Python框架，用于构建和执行数据处理流水线。其核心设计旨在实现高度的灵活性和可测试性。

**核心特性:**

- **插件化架构**: 所有处理步骤都封装为独立的插件。
- **分层配置**: 全局、插件默认、案例特定三级配置，灵活且易于管理。
- **双执行模式**: 支持完整的流水线执行和单个插件的独立执行，极大地方便了开发与调试。

---

## 核心概念

- **流水线 (Pipeline)**: 在案例的 `case.yaml` 中定义的一系列有序的插件执行步骤。
- **插件 (Plugin)**: 位于 `modules/` 目录下的一个独立的Python类，负责一项具体的处理任务（如数据转换、质量检查等）。
- **案例 (Case)**: 位于 `cases/` 目录下的一个独立的执行场景，包含了该场景所需的数据、配置和产出物。
- **配置 (Configuration)**: 框架的灵魂。配置分为三层，加载时高优先级会覆盖低优先级：
  1.  **插件默认配置** (`<plugin_name>.yaml`): 与插件代码并存，定义了插件的默认参数。
  2.  **全局配置** (`config/global.yaml`): 为所有案例提供基础的公共配置。
  3.  **案例特定配置** (`cases/<case_name>/case.yaml`): 为特定执行场景定义的流水线和覆盖参数。

---

## 项目结构

```
.
├── cases/             # 存放所有执行案例
│   └── case1/         # 示例案例
│       ├── case.yaml
│       └── input/
├── config/            # 全局配置文件
│   └── global.yaml
├── core/              # 框架核心工具与逻辑
│   ├── base_plugin.py
│   ├── config_manager.py
│   ├── pipeline_runner.py
│   └── plugin_helper.py
├── logs/              # 运行日志
├── modules/           # 所有可用的插件
│   ├── quality/
│   └── signals/
├── demo_run.py        # 完整流水线的执行入口
└── requirements.txt   # 项目依赖
```

---

## 使用方法

### 1. 环境准备

确保您已安装 Python 和 pip。然后通过以下命令安装项目依赖：

```bash
pip install -r requirements.txt
```

### 2. 运行完整流水线

要执行一个案例中定义的完整流水线，请使用 `demo_run.py`。

```bash
# 示例：执行 case1 的完整流水线
python demo_run.py --case cases/case1
```

此命令会加载 `cases/case1/case.yaml`，并按顺序执行其中 `pipeline` 定义的所有插件。

### 3. 独立执行插件（用于开发与调试）

这是本框架的一个关键特性。您可以独立运行任何单个插件，并让它加载指定案例中的配置，从而完美复现其在流水线中的运行环境。

**命令格式:**
```bash
python <插件的.py文件路径> --case <案例目录路径>
```

**示例:**
```bash
# 独立运行 DemoCheck 插件，并应用 case1 中的配置
python modules/quality/demo_check.py --case cases/case1
```

---

## 如何创建新插件

1.  在 `modules/` 下的一个子目录中，创建一个新的 Python 文件。
2.  在该文件中，创建一个继承自 `core.base_plugin.BasePlugin` 的类。
3.  实现 `run(self, context)` 方法，这是插件的核心逻辑。
4.  (可选) 在相同目录下创建一个同名的 `.yaml` 文件，为插件提供默认配置。
5.  (推荐) 在文件末尾添加独立执行入口，只需调用 `run_plugin_standalone` 即可：
    ```python
    if __name__ == "__main__":
        from core.plugin_helper import run_plugin_standalone
        run_plugin_standalone(plugin_class=YourNewPluginClass)
    ```
