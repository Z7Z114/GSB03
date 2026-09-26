# 激光测振会议纪要系统（合法授权安全测试用途）

> ⚠️ 本项目**仅用于合法授权的安全测试 / 声学研究**。请勿用于任何未经授权的窃听或入侵用途。

在授权测试场景中，激光测振仪可以从远处（例如窗玻璃）拾取室内声场的微弱振动，还原出可辨识的
语音。本项目把这条链路工程化：**音频极端增强 → 转写与说话人区分 → 声源定位 → 摘要 →
加密邮件发送**，并提供 WebSocket 实时进度推送。

前后端分离：

- **后端**（`backend/`，FastAPI）：音频增强（去卷积 / 谱减 / 维纳滤波）、Whisper 转写、
  pyannote 说话人区分、GCC-PHAT TDOA 声源定位、OpenAI 摘要、Fernet 加密邮件、任务状态管理。
- **前端**（`frontend/`，Vue 3 + Element Plus + ECharts）：处理页、定位可视化、转写浏览。

## 目录结构

```
.
├── run_server.py               # 后端启动入口
├── run_complete_pipeline.py    # 命令行完整流程示例
├── backend/
│   ├── main.py                 # FastAPI 应用、路由、任务管理、WebSocket
│   ├── audio_processor.py      # 极端低信噪比音频增强
│   ├── transcriber.py          # Whisper 转写 + pyannote 说话人区分
│   ├── source_localization.py  # GCC-PHAT TDOA 声源定位与扫描
│   ├── summary_generator.py    # OpenAI 会议摘要 + Markdown 生成
│   ├── encrypted_email.py      # Fernet 加密 + 邮件发送
│   └── tests/                  # pytest 测试
├── frontend/                   # Vue 3 前端
├── requirements.txt            # 轻量依赖（可离线跑测试）
├── requirements-ml.txt         # librosa / Whisper / pyannote 等重型可选依赖
├── .env.example
├── CLAUDE.md                   # 本仓库工程规则，动手前先读
└── README.md
```

## 运行方式

后端（Python 3.11+）：

```bash
pip install -r requirements.txt
python run_server.py                 # http://localhost:8000
```

测试：

```bash
cd backend && python -m pytest -q
```

`requirements.txt` 只含轻量依赖。`librosa` / `soundfile` / Whisper / pyannote / OpenAI / SMTP
（见 `requirements-ml.txt`）都是**可选的**：未安装或未配置时走确定性的离线分支，
因此后端与测试可在无网络、无 GPU、不调用任何外部 API 的环境下跑通。

## HTTP / WS 接口一览

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/` | 服务信息与端点清单 |
| GET | `/api/health` | 健康检查（含各模型是否已加载） |
| POST | `/api/process/audio` | 上传音频并排队处理（背景任务） |
| GET | `/api/tasks/{task_id}` | 单个任务状态 |
| GET | `/api/tasks` | 全部任务 |
| GET | `/api/download/{task_id}` | 下载结果（`file_type=markdown\|json`） |
| POST | `/api/process/localization` | 多路麦克风信号 → 声源定位 |
| WS | `/ws/realtime` | 实时进度与定位推送（`ping` / `audio_chunk`） |
| POST | `/api/encrypt` | 加密一段 Markdown |
| POST | `/api/decrypt` | 解密上传的密文 |

## 行为规格（验收标准）

本节是本次修复的验收依据，逐条以本节为准。

### A. 加密与解密

1. `POST /api/encrypt` 与 `POST /api/decrypt` 在必填字段缺失时返回 `422`；
   参数非法（如空 `key`）时也必须拒绝，不得静默按「未加密」处理。
2. `MarkdownEncryptor` **未配置密钥**时不得假装加密：`encrypt_markdown` 必须明确表示
   「未加密」，且调用方（`/api/encrypt`）必须让调用者能从响应得知内容并未加密。
3. `decrypt_markdown` **不得把解密失败伪装成成功**：用错误的密钥解密时，当前实现会把密文
   原样当成明文返回（`decode(errors='replace')`），必须改为抛出/返回明确的失败，
   不得返回密文本身冒充明文。
4. 加密→解密的往返必须保持内容一致；`encrypt_markdown` 返回值需给出使用的加密方法。

### B. 邮件发送

5. `EmailSender.send_encrypted_email` 在 SMTP **未配置**时不得返回 `success: True`：
   必须如实表示未投递（`success: False` 并带可读原因），而当前实现返回
   `success: True` + `"Email would be sent if SMTP were configured"`，会让上游把
   「没发出去」当成「已发送」。
6. `MeetingMinutesDispatcher.generate_and_dispatch` 的 `email.success` 必须与真实投递结果一致；
   未配置 SMTP 时不得为 `True`。

### C. 任务与下载

7. `POST /api/process/audio` 必须校验上传内容：空文件不得被接受为有效任务
   （当前空文件也会返回 `200` + `queued`）。
8. 任务状态只允许已定义的状态值；处理失败时必须如实标记为 `failed` 并带上原因，
   不得停留在 `processing` 或谎报 `completed`。
9. `GET /api/download/{task_id}` 仅在任务 `completed` 且存在结果时返回文件；
   未知任务 `404`、未完成或无结果 `400`、`file_type` 非法 `400`。

### D. 声源定位

10. `POST /api/process/localization` 的入参必须校验：`scan_range` 必须为正数、`resolution`
    必须是合理正整数（如 `>= 2`）；非法取值返回 `422`，不得落到 `500`。
11. 音频依赖缺失属于「服务不可用」，必须返回 `503`，而不是把 `NoneType` 报错包成 `500`。
12. `SoundSourceLocalization` 的算法边界必须稳健：
    - `gcc_phat` 对空信号不得抛 `ValueError`，应给出可预期结果或明确异常；
    - `scan_for_sources` 在 `resolution` 过小（如 `1`）或为 `0` 时不得抛 `IndexError` /
      `ValueError`，应拒绝或返回空结果；
    - `process_localization` 在信号数不足时返回带 `success: False` 的结果而不是抛异常。
13. `real_time_localization_update` 在只给一路 1D 信号时（无法做 TDOA）必须返回一个
    可用的位置与置信度，不得因为内部数组问题抛异常。

### E. 转写与说话人

14. `WhisperTranscriber` 在模型未加载时走离线分支，**该分支的结果必须可识别**
    （当前靠 `note` 字段标注），不得让调用方误以为是真实转写结果。
15. `PyannoteDiarizer` 的说话人数参数必须校验：`num_speakers <= 0` 时当前会
    `IndexError`（`-1`）或静默改成默认 3（`0`），必须统一拒绝或按规格归一化，
    不得崩溃。
16. `MeetingTranscriptIntegrator.process_meeting_audio` 的返回必须保持
    `success` / `full_text` / `segments` / `speaker_stats` 等既有字段。

### F. WebSocket 广播

17. `ConnectionManager.broadcast` 必须对单个坏连接免疫：某个连接 `send_json` 抛异常时，
    必须把它从 `active_connections` 摘除，并**继续向其余连接广播**。
    当前实现用裸 `except: pass` 吞掉异常但**不摘除**连接，坏连接会永久堆积。
18. `disconnect` 对不在列表中的连接重复调用不得抛异常（幂等）。

### G. 不得回归的既有行为

19. `/`、`/api/health`、`/api/tasks`、`/api/tasks/{id}`、合法的 `/api/download/{id}`
    以及合法参数的 `/api/process/localization`（依赖可用时）必须保持可用。
20. `summary_generator` 的 Markdown 生成、`transcriber` 的 `generate_markdown_transcript`、
    加密往返、`gcc_phat` 对正常信号的时延估计结果必须保持原有语义。

## 变更说明

以下问题已按「行为规格」逐条修复，每条注明根因与修法：

- **错误密钥解密返回密文冒充明文**：`MarkdownEncryptor.decrypt_markdown` 在解密失败或未配置
  密钥时用 `decode(errors='replace')` 把密文原样返回。现改为抛出 `ValueError`（密钥错误 /
  未配置密钥），`/api/decrypt` 据此返回 `success: false` 与错误原因，不再返回 `content`。
- **未配置 SMTP 却报告发送成功**：`EmailSender._mock_send_email` 返回 `success: True`。
  现改为 `success: False` 并带「SMTP 未配置，邮件未发送」原因，`generate_and_dispatch`
  的 `email.success` 随之与真实投递结果一致。
- **空音频文件也能创建任务**：`/api/process/audio` 未校验上传内容。现先读取文件，
  空内容返回 `400` 且不创建任务；保存失败时也会清理已注册的任务记录。
- **定位接口参数越界直接 500**：`/api/process/localization` 未校验 `scan_range` /
  `resolution`。现 `scan_range <= 0` 或 `resolution < 2` 返回 `422`；`HTTPException`
  不再被兜底 `except` 包成 `500`；音频依赖缺失仍为 `503`；`scan_range` / `resolution`
  也真正透传给扫描算法，不再只是回显。
- **定位算法边界抛异常**：`gcc_phat` 对空信号做零长度 FFT 抛 `ValueError`，现返回
  可预期的 `0.0`；`scan_for_sources` 在 `resolution < 2` 时对空数组求 `max` 抛
  `ValueError`，现返回空结果并附错误说明；`real_time_localization_update` 单路 1D
  信号时返回值缺少 `confidence`、且 `previous_estimate` 为 list 时会 `AttributeError`，
  现统一返回可用的 `position` 与 `confidence`。
- **异常说话人数导致崩溃或静默改值**：`PyannoteDiarizer.diarize` 对 `num_speakers <= 0`
  会 `IndexError`（`-1`）或静默改成 3（`0`）。现统一拒绝并返回
  `success: False` 与错误原因。
- **WebSocket 坏连接堆积并阻断广播**：`ConnectionManager.broadcast` 用裸 `except: pass`
  吞掉异常但不摘除连接。现广播时把发送失败的连接从 `active_connections` 摘除，
  并继续向其余连接广播；`disconnect` 保持幂等。
- **任务状态值不受约束**：`update_task_status` 接受任意字符串。现只允许
  `queued / processing / completed / failed`，其余值抛 `ValueError`。
- **加解密接口空密钥被静默当成「未加密」**：`/api/encrypt` 与 `/api/decrypt` 现对
  空白 `key` 返回 `422`；未配置密钥时 `encrypt_markdown` 仍以 `method: "none"`
  明确表示未加密。

## 技术栈

- 后端：FastAPI、NumPy、SciPy、SoundFile、librosa、Whisper、pyannote、OpenAI、cryptography
- 前端：Vue 3、Element Plus、ECharts、Socket.IO client、Vite
- 测试：pytest（`backend/tests`）

## 许可证

MIT License（**仅限合法授权的安全测试用途**）
