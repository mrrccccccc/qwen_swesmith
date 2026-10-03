# Qwen3.6 + SWE-smith：Windows / Linux 共用 Python 程序

主入口 `run.py`，安装入口 `setup_env.py`。下载、数据处理、SFT、DPO、曲线、
本地文本推理和 CPU 模型导出均由同一套 Python 代码调用，不依赖 Bash、
PowerShell 脚本、source、export、tee、chmod 或激活虚拟环境。
按用户要求，本次修改后未运行验证或 GPU 实验；跨平台代码不等于经过两系统实测。

## 硬件与系统范围

| 功能 | 原生 Windows | Linux |
|---|---|---|
| 模型/数据下载、许可查询、数据清洗、曲线 | Python 3.12 | Python 3.12 |
| SFT / DPO / 本地文本推理 | CUDA PyTorch；需足够显存 | CUDA PyTorch；需足够显存 |
| CPU 合并导出 | 足够主机内存 | 足够主机内存 |
| vLLM 正式长上下文服务 | 官方 CUDA 后端需 Linux/WSL2 | 使用独立 vLLM 环境 |
| 四项官方容器/Agent 评测 | 通过 Linux/WSL2 操作；不宣称全部框架原生支持 Windows | 安装对应官方框架并接入 |

**24GB 仍不能装下本项目 BF16 的 35B 基座。** 更换启动程序不会消除显存限制。
80GB 是短窗口候选，H200 141GB 更有余量；没有实机保证。
专家冻结、attention LoRA rank=8、micro batch=1、梯度累积16。
Windows 不强制安装 Linux 专用的 flash-attn、mamba-ssm、DeepSpeed 或 Triton；
模型采用 Transformers 的 PyTorch/SDPA 路线，缺少专用内核时速度可能明显下降。
实现依赖的第三方模型内核仍需在目标机器上实际确认。

## 1. 安装（只需一次）

安装 Python 3.12 和适合 GPU 的 NVIDIA 驱动。解压后进入项目根目录。

Windows CMD / PowerShell：
```text
py -3.12 setup_env.py --cuda cu128
```

Linux：
```text
python3.12 setup_env.py --cuda cu128
```

脚本自动创建项目内 `.venv`，安装 PyTorch 2.8.0 + torchvision 0.23.0 的官方
CUDA wheel、共享依赖和本项目，并写 dependencies.lock.txt。
cu126/cu128/cu129 可选，须与驱动兼容；--cuda cpu 仅用于数据处理。
requirements.txt 只列共享依赖，PyTorch 约束另存 constraints_torch.txt。

后面的入口自动选择 `.venv/Scripts/python.exe` 或 `.venv/bin/python`，
不需要 activate，也不受 PowerShell 脚本执行策略限制。
如果 Windows 没有 python 命令，下方命令把 python 换成 py 即可。

## 2. 完整下载模型和数据
```text
python run.py download
python run.py licenses
```

本地保存：
- assets/models/Qwen3.6-35B-A3B/：完整原权重、tokenizer、processor、配置。
- assets/datasets/SWE-smith/：任务表全部 parquet。
- assets/datasets/SWE-smith-trajectories/：原始轨迹全部 parquet。
- data/licenses.json：源仓库许可清单，UNKNOWN 默认排除。

下载固定 revision 并保存 SHA256；之后加载只接受本地目录，local_files_only=True，
Hub 离线。修改存储位置时，要同时更新下载和使用配置。
Windows YAML 路径推荐 D:/qwen_assets/...，或用单引号包裹反斜杠路径。
官方模型和数据 revision 保持上一版固定值，不在本次修改时更换。

## 3. 生成数据
```text
python run.py prepare
```

默认是明确标注的 **development 模式**，不会被未填写的官方 benchmark 配置阻塞。
默认 data/exclusion_policy.json 是空的开发排除清单，不意味着已证明无评测泄漏。
默认运行不能当作满足原题的正式面试实验。可填写开发排除仓库/任务/公开 prompt。
生成 sft_train/val、dpo_train/val、audit、stats、provenance 到 data/processed/。
轨迹使用 tool split；按 instance_id 关联；成功轨迹 SFT，同任务成功/失败补丁 DPO。
未知来源许可、无效轨迹、重复轨迹排除；同一仓库不跨训练/开发 split。

## 4. 两阶段训练
```text
python run.py sft --gpu 0
python run.py curves --run-dir outputs/sft
python run.py stage2 --gpu 0
python run.py curves --run-dir outputs/stage2
```

或用一条命令（重新处理数据并依次训练两阶段）：
```text
python run.py train-all --gpu 0
```

训练自动将 stdout/stderr 保存到 outputs/console，包含错误日志。
参数在 configs/sft_80gb.yaml、configs/stage2_80gb.yaml。
默认输出目录已使用时会报错，防止覆盖。重新实验请配置新的 output_dir，
相应更新 stage2 的 initial_adapter。
默认 SFT 500 optimizer steps、DPO 150 steps，是起步值而非实测最优。
SFT 使用2048 token重叠窗口；DPO超长pair排除并记录，数据不足会明确报错。
阶段二在 SFT best_adapter 上继续训练，冻结 SFT reference adapter，与 policy
共享基座；stage2 adapter 是完整更新后的 adapter。
无 optimizer-resume 功能，失败后用新运行目录重新训练。

输出：
- outputs/sft/best_adapter、final_adapter、定期 checkpoint。
- outputs/stage2/best_adapter、final_adapter、定期 checkpoint。
- config、启动命令、pip freeze、实际模型加载报告、LoRA目标、资源、loss、DEV结果。
- curves/：每项指标独立300dpi PNG、PDF和源CSV。

## 5. 本地文本推理（两系统同样命令）
```text
python run.py serve --gpu 0
```

上面加载 Base。停止服务后可以加载训练模型，同一时刻只启动一个服务：
```text
python run.py serve --gpu 0 --adapter outputs/sft/best_adapter
python run.py serve --gpu 0 --adapter outputs/stage2/best_adapter
```
接口 http://127.0.0.1:8000/v1/chat/completions。
服务只生成工具调用，由外部 Agent 执行工具。
默认 text-only、8192 context、1024 output budget，仅用于本地调试，不冒充
256K正式评测。SSE为缓冲兼容输出，不是逐token实时流。

## 6. CPU 导出（两系统同样命令）
```text
python run.py export --output assets/exports/base
python run.py export --adapter outputs/sft/best_adapter --output assets/exports/sft
python run.py export --adapter outputs/stage2/best_adapter --output assets/exports/stage2
```
主机内存建议128–192GB，保留视觉模块，MTP不启用；三版本保持同样导出方式。

## 7. 正式面试模式

原题要求训练前锁定四项评测。开发模式不能替代正式模式，也不能用评测反馈
选模型。先按 docs/EVALUATION.md 确认指定版本、完整任务ID、镜像、Agent、官方
runner，填写 benchmarks/manifest.json。

```text
python run.py freeze
python run.py prepare --config configs/data_formal.yaml
```

正式训练使用独立目录：
```text
python run.py sft --config configs/sft_formal.yaml --gpu 0
python run.py stage2 --config configs/stage2_formal.yaml --gpu 0
```
formal仍严格校验冻结协议，不把旧开发checkpoint自动当成正式实验。
训练前按固定协议测Base；冻结权重后再测两个训练版本。

Linux/WSL2独立vLLM环境中启动正式服务：
```text
python run.py --current-python vllm --model-dir assets/exports/base --tp 1
```

--current-python明确使用当前解释器，避免入口自动选到训练环境的.venv。
需要安装官方vLLM，模型卡建议>=0.19.0，锁定实际安装版本。
原生Windows vllm命令会明确提示系统限制；本地文本调试可使用serve。
不要将vLLM混装到训练环境而改变训练torch。

另一终端在官方runner接入后运行：
```text
python run.py evaluate --variant base
```
依次切换sft/stage2本地导出服务，再运行 --variant sft/--variant stage2。
四项完整结果产生后：
```text
python run.py summarize
```

四套官方框架未内置，指定版本和normalized.jsonl映射仍需接入。
Windows可操作Linux服务；官方Agent和容器执行仍受各框架系统限制。
不会仅凭通用启动器声称完成官方评测。

## 文件结构
- setup_env.py：两系统安装；run.py：统一入口与虚拟环境选择。
- src/qwen_swesmith/portable.py：跨平台子命令、CUDA选择、Python日志。
- configs/：下载、开发数据、训练、推理，以及正式配置的继承覆盖。
- src/qwen_swesmith/：数据、模型、编码、训练、推理、导出、评测和统计。
- docs/：硬件、方法、官方评测限制、提交要求。
- SOURCE_CODE.md：各文件完整源码；tests/是可选测试，本次没有执行。

没有Bash启动脚本。源码项目不包含已训练checkpoint、正式成绩或虚构报告。
