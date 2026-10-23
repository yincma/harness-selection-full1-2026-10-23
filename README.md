# Harness 选型实验：full1 公开复核附件

2026-10-23，使用 Kiro CLI / claude-haiku-4.5，在 5 道代码题上比较直接回答 A、固定工作流 B、四次执行后挑选 Bx4，以及修改系统提示的 H²-lite C。

本仓库是随文章发布的证据附件。它可以核对正式结果、图表数据、方法边界与公开节选；也可以从已有 SVG/HTML/数据重新渲染四图。它不是完整的一键实验复跑包。

## 阅读入口

- **[完整附件索引](evidence-index.md)**：四图、30 条节选及原始定位。
- [正式报告](source/runs/full1/report.json) · [预注册判定](source/runs/full1/judgement.md) · [预注册规则](source/PREREGISTRATION_full1.md)。
- [复核与重建方法](reproduce-notes.md) · [分析边界及未解决的版本追溯问题](analysis-notes.md)。
- [公开前检查记录](PUBLICATION_REVIEW.md) · [公开文件 SHA-256](SHA256SUMS.json) · [第三方来源与许可](THIRD_PARTY_NOTICES.md)。

## 结果口径

仅报告本次 5 题和该模型的观察，不外推其他模型或任务。连续题按预先规定的分差阈值逐题判定，不是显著性检验；二值结果仅为单次观察。C 对 Bx4 为主要比较。C 是参照 Harness² 思路的简化版，未运行官方实现。

credits 是调用积分，不能直接当作货币。四次执行匹配不代表积分相同。B_1 实际共享但按各组定义计入，分组积分不能相加作为整场实际消耗。报告中的 Bx4/C e2e_s 为依赖路径估算，不是完整排队墙钟实测。

## 完整性与重建

```sh
python3 scripts/verify_bundle.py
```

依赖安装、中文字体与离线重绘命令见 [reproduce-notes.md](reproduce-notes.md)。公开包没有账户认证、完整会话流、隐藏答案或原始实验环境；未重新运行任何正式实验。
