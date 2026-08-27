# 判题 worker 规格（`backend/judge/`）

## 角色

独立进程 `python -m judge.worker`，与 backend 共用同一个 SQLite（同一 `DATABASE_URL`），轮询 `submissions` 表领取 `pending` 提交，用一次性 Docker 容器评测，写回结果。worker 复用 `app.db` / `app.models`（把 backend 目录加入 sys.path 或作为包安装）。

## 判题镜像

- `judge/Dockerfile.python` → 镜像 `leetpath-judge-python`：基于 `python:3.12-slim`，无额外依赖。
- `judge/Dockerfile.cpp` → 镜像 `leetpath-judge-cpp`：基于 `gcc:13`。
- worker 启动时检查两个镜像存在（`docker image inspect`），缺失则以清晰报错退出并提示构建命令。
- 镜像在宿主机 docker daemon 中构建（compose 里配置 build 段或手动 `docker build`，见 README）。

## 领取提交

每 `POLL_INTERVAL`（默认 1s）：

```sql
UPDATE submissions SET status='judging' WHERE id=:id AND status='pending'
```

按 id 升序取最早 pending，rowcount=1 才算领取成功（防多 worker 重复）。单 worker 顺序处理即可，不做并发。单 worker 启动时先把进程异常退出遗留的 `judging` 提交恢复为 `pending`。

## 评测流程（一次提交）

1. 建临时目录 `<tmp>/<submission_id>/`：`main.py` 或 `main.cpp`（用户代码），`tests/NNN.in`（全部用例，含样例与隐藏）。若提交 `io_mode=leetcode`，worker 把用户的 `class Solution` / 设计类套上读入 harness 再写入源文件；用例与比对规则仍是 ACM stdin/stdout。无 `leetcode_spec` 时记 `CE`。
2. **cpp 先编译**（独立容器，输出到该目录）：

   ```
   docker run --network none --read-only --tmpfs /tmp:size=32m \
     --memory 512m --memory-swap 512m --cpus 1 --pids-limit 64 \
     --cap-drop ALL --security-opt no-new-privileges --user 65534:65534 \
     -v <dir>:/work -w /work leetpath-judge-cpp \
     g++ -O2 -std=c++17 -o main_bin main.cpp
   ```

   编译容器与运行容器一样使用唯一名称，退出后先 inspect、再在 finally 中强制删除。能确认编译器已运行且非零退出时 → 整题 `CE`，stderr 截断 4000 字符存入 `compile_output`；无法确认容器实际退出时按 Docker 基础设施异常记 `IE`。
3. **逐用例运行**（每个用例一个一次性容器，按 ordinal 升序）：

   ```
   docker run --network none --read-only --tmpfs /tmp:size=32m \
     --memory <memory_limit_mb>m --memory-swap <memory_limit_mb>m --cpus 0.5 --pids-limit 64 \
     --cap-drop ALL --security-opt no-new-privileges --user 65534:65534 \
     -v <dir>:/work:ro -w /work <image> \
     sh -c "timeout -s KILL <limit_s> <cmd> < tests/NNN.in"
   ```

   - python3: image=`leetpath-judge-python`, cmd=`python3 main.py`
   - cpp: image=`leetpath-judge-cpp`, cmd=`./main_bin`（注意 main_bin 在 /work 下，--read-only 不影响执行）
   - 容器不使用 `--rm`，以便通过 `docker inspect -f '{{json .State}}'` 读取可信的 `Status`、`ExitCode` 和 `OOMKilled`；worker 在 finally 中强制删除容器。
   - `<limit_s>` = ceil(time_limit_ms/1000)，另加外层进程超时 `limit_s+15` 兜底（含容器启动开销），外层超时视为 TLE。
4. 每个用例判定：
   - 非零 `docker run` 必须先确认容器状态为 `exited`；容器 ExitCode 124 记 `TLE`，137 时根据 `OOMKilled` 区分 `MLE`，否则记 `TLE`
   - stdout + stderr 合计超过 1 MiB 时立即终止容器并记 `RE`；编译输出超限记 `CE`
   - 其他非零退出 → `RE`（stderr 截断 500 字符记入该用例 detail）
   - stdout/stderr 是用户程序或编译器可控内容，不得靠其中的 `docker:`、`cannot connect` 等文本判断基础设施故障
   - 零退出 → 比对 stdout 与 expected_output：**规范化**（每行去行尾空白、整体去末尾空行）后相等 → `AC`，否则 `WA`（记录实际输出截断 500 字符）
   - 单用例 runtime_ms：容器运行的外层 wall time（近似值，含启动开销，文档注明）
5. 整题状态：全部 AC → `AC`；否则取**第一个非 AC 用例**的状态。遇到非 AC 即停止后续用例（fail-fast）。
6. 写回：`status`、`runtime_ms`（各用例最大值）、`detail`（JSON）：

   ```json
   [{"ordinal": 1, "is_sample": true, "status": "AC", "runtime_ms": 123,
     "input": "...", "expected": "...", "output": "..."}]
   ```

   - `input/expected/output` 仅样例用例（is_sample=true）包含，且各截断 1000 字符；隐藏用例只有 ordinal/is_sample/status/runtime_ms（+RE 时的 stderr）。
7. 任何基础设施异常（docker 不可用、镜像缺失、非零 `docker run` 且没有可验证的已退出容器等）→ 状态 `IE`，异常信息入 `compile_output`。**异常不能使 worker 退出**，记录后继续轮询。
8. 清理临时目录（finally）。

## 配置（环境变量）

- `DATABASE_URL`（与 backend 一致）
- `POLL_INTERVAL`（默认 1.0）
- `JUDGE_IMAGE_PYTHON`（默认 `leetpath-judge-python`）、`JUDGE_IMAGE_CPP`（默认 `leetpath-judge-cpp`）
- `DOCKER_BIN`（默认 `docker`）

日志用标准 `logging`，INFO 级别输出领取/完成一行摘要。

## 验收标准

本地（装了 Docker 的机器）用一道 A+B 题手动验证六种状态：正确解 AC、输出错误 WA、死循环 TLE、C++ 语法错误 CE（compile_output 有编译器输出）、除零 RE、巨量内存 MLE。
