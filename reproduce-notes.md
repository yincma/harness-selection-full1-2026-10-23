# 复核与重建说明

这些公开附件可重新渲染四图并核对公开节选、口径与分数。它们不是完整的一键复跑发行包；没有打包整个 SWE 仓库、运行虚拟环境或隐藏答案。本次编辑没有重跑正式实验，也没有向 full1 增加结果。

## 先核对这几个入口

- 正式数据：[report.json](source/runs/full1/report.json)；预注册判定：[judgement.md](source/runs/full1/judgement.md)。
- 原始运行根目录未分发；路径统一改为实验内相对路径。截图节选定位：[provenance.json](provenance.json)；源文件快照：[source-snapshots.json](source-snapshots.json)。
- 工作流与共享 B_1：[run_full.py](source/run_full.py)；积分和时间口径：[report_full.py](source/report_full.py)。
- 评分规则：[PREREGISTRATION_full1.md](source/PREREGISTRATION_full1.md)、[judge_full.py](source/judge_full.py)。
- 约束原文：[propose.md](source/prompts/propose.md) 与 [compose.md](source/prompts/compose.md) 均对生成提示要求 at most 600 words、no solution code。

## 重建四图

公开包可离线重绘图 4，并把随附 SVG 和两个只读 HTML 阅览页重新渲染为 PNG。它不从完整原始日志重新抽取字段，因为这些日志没有分发；节选定位和原始哈希保留在 provenance.json。

```sh
python3 -m pip install -r requirements-figures.txt
python3 -m playwright install chromium
python3 scripts/rebuild_figures.py --font /path/to/a/CJK-font.ttf --output rebuilt
```

`--font` 可省略，但缺少中文字体时文字可能无法正确显示。原图使用 Hiragino Sans GB；不同字体和浏览器版本会影响像素，不改变数据。重新渲染输出到单独目录，不覆盖随附的历史图片，不调用 Kiro 或重跑实验。

完整性检查：`python3 scripts/verify_bundle.py`。源码快照保留作审查用途；缺少完整任务模板、评分器和原始日志，不能直接运行 source/run_full.py 来复现实验。common.py 的默认值服务于早期试点；正式运行参数以 run-manifest.json 为准。

## 保留的判定规则与失败处理

逐题比较，不跨题平均。连续题 T=max(B 四次极差,3 个百分点)，超过阈值才判优于；差距未超过阈值时写“未检出差异”。二值题只有 B 四次全失败而该组成功，或 B 四次全成功而该组失败，才判优于或劣于，并注明单次观察；其余无法区分。全部满分只比成本。Q1 的“直接调用即可”还要求 A 不差于 B 且更便宜。

基础设施失败最多重跑 2 次；超时算有效；改进器两次不合格则 C 记 0；挑选员两次不合格则改选可见测试最高者。full1 没有最终失败、跳过或超时，CommonMark 一次探测因基础设施故障重跑一次。

成本：A=一次回答；B=B_1；Bx4=B_1-B_4+挑选；C=B_1+提出+两次探测+合成+最终。B_1 在实际调度中复用，但每组分析按自身定义计入它，不能把四组积分相加当作整场实际消耗。

时间：A/B 为其单次运行的实测 wall_s；Bx4 估算=max(B 四次 wall_s)+挑选 wall_s；C 估算=B_1+提出+max(两探测)+合成+最终。sum_s 是调用时间累加。估算不含本机并发上限造成的排队，不是整个工作流的实测墙钟时间。

## 想复跑时还需固定

模型 claude-haiku-4.5、Kiro CLI 2.33.1、主机 Apple M4/16 GB/macOS 15.6.1、调度 Python 3.13.7；SWE 的任务虚拟环境按各题配置。全局 steering/skills 不继承；agent 读写/命令经守卫；运行时无隐藏评分测试/参考答案。每次 agent 最长 45 分钟，A、改进器、挑选员单次最长 20 分钟；最多两个 kiro-cli 进程。

HumanEval 的固定 commit、种子、选择规则；CommonMark 规范版本、可见例列表；JSON Schema suite_commit、排除/分组规则；SWE 数据修订、base_commit、筛选与环境验证规则，均保留在 source/tasks/ 的元数据中。HumanEval 可见 docstring 示例；规范题可见其划分出的示例；SWE 可读取已有仓库测试，但新增 issue 评分测试交付后才注入。

素材包记规则定稿为 00:49；PREREGISTRATION_full1.md 写“00:50 JST 前后”。本文只保留双方一致的相对顺序（full1 已启动、只完成 HumanEval、作者声明未看隐藏分数），准确分钟待作者核验。
