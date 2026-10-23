# full1 公开复核附件与来源索引

本附件支持核对文章四图、正式分数、预注册判定和挑选员段落。没有重跑实验。图 2、图 3 为历史记录或可见输入重新排版后的截图，不是原始运行时抓拍。

- [正式报告](source/runs/full1/report.json) · [正式判定](source/runs/full1/judgement.md) · [预注册](source/PREREGISTRATION_full1.md)
- [重建与口径说明](reproduce-notes.md) · [局限与版本追溯](analysis-notes.md)
- [来源定位与原始哈希](provenance.json) · [源码快照哈希](source-snapshots.json) · [公开文件完整性清单](SHA256SUMS.json)

## 四张图片

| 图 | 图片 | 可编辑或重建来源 |
|---|---|---|
| 1 | [fig-01-workflows.png](fig-01-workflows.png) | [fig-01-workflows.svg](fig-01-workflows.svg) |
| 2 | [fig-02-execution-records.png](fig-02-execution-records.png) | [fig-02-record-reader.html](fig-02-record-reader.html) |
| 3 | [fig-03-task-examples.png](fig-03-task-examples.png) | [fig-03-task-reader.html](fig-03-task-reader.html) |
| 4 | [fig-04-quality-credits.png](fig-04-quality-credits.png) | [fig-04-quality-credits.svg](fig-04-quality-credits.svg) |

## 节选来源

原始路径均为实验目录内的相对路径。完整原始运行文件未分发时，原始哈希只作为作者保留原件的标识；读者可以独立核对公开节选、分发的源码和图表数据，不能仅凭哈希复验未分发的全部原件。

### 1. fig02-A-record.txt

- 公开节选：[fig02-A-record.txt](evidence/fig02-A-record.txt)
- 原始相对路径：`runs/full1/jsonschema/A_direct/done.json`
- 原始 SHA-256：`a172c30d6fb01d7965b9192a7444b9eaccb89f100d58110d5c4e4b7a3032e7d6`
- 定位：`{"json_pointers": ["/state", "/status", "/tool_calls", "/out/files_written"], "format": "one field per line"}`

### 2. fig02-A-reply.txt

- 公开节选：[fig02-A-reply.txt](evidence/fig02-A-reply.txt)
- 原始相对路径：`runs/full1/jsonschema/A_direct/run/run.json`
- 原始 SHA-256：`1f1e0f884c6b2c30ee529e61c5f97ac5ce5a98770edec5aafb3e8e0500c17dd6`
- 定位：`{"json_pointer": "/final_text", "selected_lines": [1, 8]}`

### 3. fig02-B-tool-titles.txt

- 公开节选：[fig02-B-tool-titles.txt](evidence/fig02-B-tool-titles.txt)
- 原始相对路径：`runs/full1/jsonschema/B_1/run/events.jsonl`
- 原始 SHA-256：`28d465c8a45cd32e214cba2ef4988a7753f55fc2fbf7210975c04cbe14aae4f4`
- 定位：`{"jsonl_lines_and_title_fields": [[17, "Reading listing ., listing spec"], [141, "Creating jsonschema_impl.py"], [149, "Running: ./run_tests.sh --max-fail 5"], [223, "Editing jsonschema_impl.py"], [1737, "Running: ./run_tests.sh"]]}`

### 4. fig02-B-record.txt

- 公开节选：[fig02-B-record.txt](evidence/fig02-B-record.txt)
- 原始相对路径：`runs/full1/jsonschema/B_1/done.json`
- 原始 SHA-256：`f8cf153bcb703b0d36a2130b46d5724032eb5dfc25cdb2ee90e34c109abdaf73`
- 定位：`{"json_pointers": ["/state", "/status", "/tool_calls"]}`

### 5. fig02-B-visible.txt

- 公开节选：[fig02-B-visible.txt](evidence/fig02-B-visible.txt)
- 原始相对路径：`runs/full1/jsonschema/B_1/visible_result.txt`
- 原始 SHA-256：`9da7a6611fe7f8106264049a7c651e26d66c376328497791a5b76bdadb162241`
- 定位：`{"line": 1}`

### 6. fig02-Bx4-B_1.txt

- 公开节选：[fig02-Bx4-B_1.txt](evidence/fig02-Bx4-B_1.txt)
- 原始相对路径：`runs/full1/jsonschema/B_1/done.json`
- 原始 SHA-256：`f8cf153bcb703b0d36a2130b46d5724032eb5dfc25cdb2ee90e34c109abdaf73`
- 定位：`{"json_pointers": ["/state", "/status"], "row_label": "B_1"}`

### 7. fig02-Bx4-B_2.txt

- 公开节选：[fig02-Bx4-B_2.txt](evidence/fig02-Bx4-B_2.txt)
- 原始相对路径：`runs/full1/jsonschema/B_2/done.json`
- 原始 SHA-256：`2c170688438e17ff2e10012acea38164d6438a005be62e00bd4c3c20bd9cb726`
- 定位：`{"json_pointers": ["/state", "/status"], "row_label": "B_2"}`

### 8. fig02-Bx4-B_3.txt

- 公开节选：[fig02-Bx4-B_3.txt](evidence/fig02-Bx4-B_3.txt)
- 原始相对路径：`runs/full1/jsonschema/B_3/done.json`
- 原始 SHA-256：`f795350cb669ae2810f6621fddb272cc06c436446d7c39e673dd77204ec98d4c`
- 定位：`{"json_pointers": ["/state", "/status"], "row_label": "B_3"}`

### 9. fig02-Bx4-B_4.txt

- 公开节选：[fig02-Bx4-B_4.txt](evidence/fig02-Bx4-B_4.txt)
- 原始相对路径：`runs/full1/jsonschema/B_4/done.json`
- 原始 SHA-256：`17339054e3c780f7bdf24f48fb2fbaf4959030919bc547af68467f1a955008b3`
- 定位：`{"json_pointers": ["/state", "/status"], "row_label": "B_4"}`

### 10. fig02-selector.txt

- 公开节选：[fig02-selector.txt](evidence/fig02-selector.txt)
- 原始相对路径：`runs/full1/jsonschema/Bx4_select/done.json`
- 原始 SHA-256：`44651a86c257b94108abbcad4c04d94bb92023e57d6291fbb0eaec634bfd9286`
- 定位：`{"json_pointers": ["/state", "/status", "/out"]}`

### 11. fig02-selector-choice.txt

- 公开节选：[fig02-selector-choice.txt](evidence/fig02-selector-choice.txt)
- 原始相对路径：`runs/full1/jsonschema/Bx4_select/done.json`
- 原始 SHA-256：`44651a86c257b94108abbcad4c04d94bb92023e57d6291fbb0eaec634bfd9286`
- 定位：`{"json_pointer": "/out/choice"}`

### 12. fig02-C_propose.txt

- 公开节选：[fig02-C_propose.txt](evidence/fig02-C_propose.txt)
- 原始相对路径：`runs/full1/jsonschema/C_propose/done.json`
- 原始 SHA-256：`384a4327c8417480e3e3785d831f7832d4e3fafd1677a15cd8cb0ee98b220480`
- 定位：`{"json_pointers": ["/state"], "stage": "C_propose", "display_alias": "tools = tool_calls"}`

### 13. fig02-C_probe_general.txt

- 公开节选：[fig02-C_probe_general.txt](evidence/fig02-C_probe_general.txt)
- 原始相对路径：`runs/full1/jsonschema/C_probe_general/done.json`
- 原始 SHA-256：`9158215515ac602de4d506453d187a20e5f65847553718d8f82097e7d5e6ff1b`
- 定位：`{"json_pointers": ["/state", "/tool_calls"], "stage": "C_probe_general", "display_alias": "tools = tool_calls"}`

### 14. fig02-C_probe_specific.txt

- 公开节选：[fig02-C_probe_specific.txt](evidence/fig02-C_probe_specific.txt)
- 原始相对路径：`runs/full1/jsonschema/C_probe_specific/done.json`
- 原始 SHA-256：`5e59876a3f9f48eb7f58d65c64505fac5025c16b45934bf46c994202c04c4a6c`
- 定位：`{"json_pointers": ["/state", "/tool_calls"], "stage": "C_probe_specific", "display_alias": "tools = tool_calls"}`

### 15. fig02-C_compose.txt

- 公开节选：[fig02-C_compose.txt](evidence/fig02-C_compose.txt)
- 原始相对路径：`runs/full1/jsonschema/C_compose/done.json`
- 原始 SHA-256：`60d0abe2e0c2a0973eaee24c8c69fd399205ab45c5eb782ebb76aae7a6cdd54f`
- 定位：`{"json_pointers": ["/state"], "stage": "C_compose", "display_alias": "tools = tool_calls"}`

### 16. fig02-C_final.txt

- 公开节选：[fig02-C_final.txt](evidence/fig02-C_final.txt)
- 原始相对路径：`runs/full1/jsonschema/C_final/done.json`
- 原始 SHA-256：`612519a7efb79d7f0f3219e5f4cea76fae8560987b35383d5a803ae6b06b5f81`
- 定位：`{"json_pointers": ["/state", "/tool_calls"], "stage": "C_final", "display_alias": "tools = tool_calls"}`

### 17. fig02-C_propose-tags.txt

- 公开节选：[fig02-C_propose-tags.txt](evidence/fig02-C_propose-tags.txt)
- 原始相对路径：`runs/full1/jsonschema/C_propose/attempt1/output.md`
- 原始 SHA-256：`3a36b308c72d6eb811b82808822245467cde67babd0208dd7a8593bae576106a`
- 定位：`{"line_numbers": [15, 45]}`

### 18. fig02-C_compose-tags.txt

- 公开节选：[fig02-C_compose-tags.txt](evidence/fig02-C_compose-tags.txt)
- 原始相对路径：`runs/full1/jsonschema/C_compose/attempt1/output.md`
- 原始 SHA-256：`f1a631af1d10507c77c67c84a0e086e0c4e7b50ae6b3f11a03b7672b16db62ef`
- 定位：`{"line_numbers": [10]}`

### 19. fig02-C-new-directive.txt

- 公开节选：[fig02-C-new-directive.txt](evidence/fig02-C-new-directive.txt)
- 原始相对路径：`runs/full1/jsonschema/C_propose/attempt1/output.md`
- 原始 SHA-256：`3a36b308c72d6eb811b82808822245467cde67babd0208dd7a8593bae576106a`
- 定位：`{"line_numbers": [22], "artifact": "prompt_general"}`

### 20. fig02-C-final-directive.txt

- 公开节选：[fig02-C-final-directive.txt](evidence/fig02-C-final-directive.txt)
- 原始相对路径：`runs/full1/jsonschema/C_compose/attempt1/output.md`
- 原始 SHA-256：`f1a631af1d10507c77c67c84a0e086e0c4e7b50ae6b3f11a03b7672b16db62ef`
- 定位：`{"line_numbers": [13], "artifact": "prompt_final"}`

### 21. fig03-humaneval-visible.txt

- 公开节选：[fig03-humaneval-visible.txt](evidence/fig03-humaneval-visible.txt)
- 原始相对路径：`tasks/humaneval/template/solution.py`
- 原始 SHA-256：`9445e82177f062459a801e24909bc856435701d82f1d67a9dad1f9d6fd0f6362`
- 定位：`{"line_numbers": [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]}`
- 随附原件：[source/tasks/humaneval/template/solution.py](source/tasks/humaneval/template/solution.py)

### 22. fig03-commonmark-visible.txt

- 公开节选：[fig03-commonmark-visible.txt](evidence/fig03-commonmark-visible.txt)
- 原始相对路径：`runs/full1/commonmark/B_1/ws/tests/visible_tests.json`
- 原始 SHA-256：`a1051629a976099cd17230ede0d968758487443543fb99a8f322c60421a9d657`
- 定位：`{"json_pointer": "/185", "example": 360, "visibility": "visible"}`

### 23. fig03-swe1-visible.txt

- 公开节选：[fig03-swe1-visible.txt](evidence/fig03-swe1-visible.txt)
- 原始相对路径：`tasks/swe1/task_prompt.md`
- 原始 SHA-256：`ede4f26730f782959bdaef63bb89711799cade7a9fa3acb5eba7f48794de938a`
- 定位：`{"line_numbers": [4, 9, 10, 11, 12, 13, 15, 16], "editorial_omitted_line_ranges": [[5, 6, 7, 8], [14]], "visibility": "task prompt passed to agent"}`
- 随附原件：[source/tasks/swe1/task_prompt.md](source/tasks/swe1/task_prompt.md)

### 24. text-cm-selector-rationale.txt

- 公开节选：[text-cm-selector-rationale.txt](evidence/text-cm-selector-rationale.txt)
- 原始相对路径：`runs/full1/commonmark/Bx4_select/attempt1/output.md`
- 原始 SHA-256：`e74ad6c10541a2e06ac72994c8e8ceb7b375b9e2a2198b7c093f8277bc309f3b`
- 定位：`{"line_numbers": [2, 4]}`
- 支撑内容：挑选员英文理由：第一条称 Attempt 1 分数最高；第三条写 Attempt 3 为 154/333、例 4 超时、HTML 块 0/22

### 25. text-cm-selector-order.txt

- 公开节选：[text-cm-selector-order.txt](evidence/text-cm-selector-order.txt)
- 原始相对路径：`runs/full1/commonmark/Bx4_select/attempt1/input.md`
- 原始 SHA-256：`059b7bef650cecf43196255d3b190270a8e7321fd1927face4efcde93ea459fb`
- 定位：`{"line_numbers": [21, 25, 203, 207, 381, 385, 549, 553]}`
- 支撑内容：挑选员看到的四份记录按 B_1-B_4 顺序编为 Attempt 1-4，及各自可见通过数

### 26. text-cm-selector-done.txt

- 公开节选：[text-cm-selector-done.txt](evidence/text-cm-selector-done.txt)
- 原始相对路径：`runs/full1/commonmark/Bx4_select/done.json`
- 原始 SHA-256：`3db150b6abc31debf5e8edb6733a02b97f46291c833091160ab868b3a74b3560`
- 定位：`{"json_pointers": ["/out/choice", "/out/best_visible"]}`
- 支撑内容：挑选结果 B_1；可见测试最高为 B_3

### 27. text-cm-B_1-visible.txt

- 公开节选：[text-cm-B_1-visible.txt](evidence/text-cm-B_1-visible.txt)
- 原始相对路径：`runs/full1/commonmark/B_1/visible_result.txt`
- 原始 SHA-256：`6336abf1963652e7a7abf6a872d00b02ba22a0d4f4ced64293795d5a53c9385d`
- 定位：`{"line_numbers": [1]}`
- 支撑内容：B_1 可见测试 142/333

### 28. text-cm-B_3-visible.txt

- 公开节选：[text-cm-B_3-visible.txt](evidence/text-cm-B_3-visible.txt)
- 原始相对路径：`runs/full1/commonmark/B_3/visible_result.txt`
- 原始 SHA-256：`d152b5ccda3f7533170724ea259f0cb0f492b940ff458e7e4d1519d85b5e22d3`
- 定位：`{"line_numbers": [1, 11, 29, 33]}`
- 支撑内容：B_3 可见测试 154/333、HTML 块 0/22、例 4 超时

### 29. text-swe2-selector-done.txt

- 公开节选：[text-swe2-selector-done.txt](evidence/text-swe2-selector-done.txt)
- 原始相对路径：`runs/full1/swe2/Bx4_select/done.json`
- 原始 SHA-256：`03da21142aff66e8160465eb0be24c5f6a469e55e66a30a95b48bb4bfa0b1b99`
- 定位：`{"json_pointers": ["/out/choice"]}`
- 支撑内容：swe2 挑选结果 B_4

### 30. text-run_full-select-order.txt

- 公开节选：[text-run_full-select-order.txt](evidence/text-run_full-select-order.txt)
- 原始相对路径：`run_full.py`
- 原始 SHA-256：`69a9452ac2b2ae1bd2671219b501fa4b663f29c2a75b70986061bf9bbcdbd611`
- 定位：`{"line_numbers": [52, 276, 288]}`
- 支撑内容：挑选员输入按 B_RUNS 固定顺序（B_1-B_4）编号为 Attempt 1-4，未打乱
- 随附原件：[source/run_full.py](source/run_full.py)
