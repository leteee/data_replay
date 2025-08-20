# 视频回叠系统 Demo

## 目录结构

- modules/: 插件目录 (signals, analysis, quality)
- utils/: 工具类和 PipelineRunner
- config/: 全局和 case 配置
- cases/: 输入输出案例
- logs/: 日志目录

## 使用方法

1. 初始化项目：

```bash
bash setup_full_demo.sh
```

2. 运行 demo：

```bash
python3 demo_run.py
```

- 输出视频：cases/case1/output/demo_video.avi  
- 日志：logs/case1_demo/pipeline.log
