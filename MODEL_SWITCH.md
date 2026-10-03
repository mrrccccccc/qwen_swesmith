# 模型切换：Qwen3-0.6B 与 Qwen3.6-35B-A3B

更新内容：支持本地文本模型与原多模态模型加载器；根据本地 safetensors 权重头估算显存，不再固定按35B计算。所有模型和 tokenizer 使用 local_files_only=True，不运行远程代码。LoRA 的基础模型仓库与版本/本地文件指纹一起记录，拒绝与另一模型的适配器混用。

本次仅编写代码，没有运行测试、模型加载或训练。

## 给现有项目打补丁

将 qwen_model_switch_patch.zip 解压到原项目根目录，覆盖同名文件。补丁不包含模型、数据、虚拟环境和已有训练结果。完整源码包也同步更新。

## 手动下载

官方文件页面：https://huggingface.co/Qwen/Qwen3-0.6B/tree/c1899de289a04d12100db370d81485cdf75e47ca
逐文件直链见 QWEN3_DOWNLOAD_LINKS.txt。

下载 config.json、generation_config.json、merges.txt、model.safetensors、tokenizer.json、tokenizer_config.json、vocab.json；LICENSE/README.md也建议保留。所有文件直接放到 assets/models/Qwen3-0.6B，别额外嵌套一层文件夹。

开发模式下缺少 snapshot_manifest.json 时自动为本地模型生成 SHA256 清单。第一次计算哈希会耗时；不需要联网。revision 使用 local-sha256 文件指纹，不会虚构已验证的上游提交。正式实验需要原题指定35B模型及固定上游版本。

## Windows / Linux 相同运行命令

在项目根目录执行。若 data/processed 已生成且配置未变，可以跳过 prepare。

```text
python run.py prepare
python run.py sft --model qwen3-0.6b
python run.py stage2 --model qwen3-0.6b
python run.py serve --model qwen3-0.6b --adapter outputs/qwen3_0_6b/stage2/best_adapter
```

仅启动基础模型：

```text
python run.py serve --model qwen3-0.6b
```

启动SFT结果：

```text
python run.py serve --model qwen3-0.6b --adapter outputs/qwen3_0_6b/sft/best_adapter
```

一条命令处理数据并训练两阶段：

```text
python run.py train-all --model qwen3-0.6b
```

手动下载后无需执行 download。网络允许时，仅下载小模型：

```text
python run.py download --model qwen3-0.6b
```

它不会再次下载数据集。

曲线与导出：

```text
python run.py curves --run-dir outputs/qwen3_0_6b/sft
python run.py curves --run-dir outputs/qwen3_0_6b/stage2
python run.py export --model qwen3-0.6b --adapter outputs/qwen3_0_6b/stage2/best_adapter --output outputs/qwen3_0_6b/exported
```

切回原模型：

```text
python run.py sft --model qwen3.6-35b
python run.py stage2 --model qwen3.6-35b
python run.py serve --model qwen3.6-35b
```

原35B模型仍需大显存GPU。本次小模型只是开发流程试跑，不能替代原题正式模型结果。

## 显存和依赖

小模型配置采用BF16、attention LoRA rank=8、序列长度2048、每次一条样本、梯度检查点；DPO共用冻结基础模型并保留reference适配器。预计适合24GB的支持BF16的NVIDIA显卡，如RTX3090/4090；未实测峰值。显存预检查按权重参数量×2字节+3GiB余量判断，不是峰值显存保证。

沿用原项目依赖安装方式（Python3.12）。数据处理的Python3.9修复保留，但不意味着所有训练依赖都支持3.9。如果使用已有环境，Qwen3至少要求transformers 4.51.0；旧版本可能报KeyError: qwen3。请保留可用CUDA版torch，别为切换模型随意重装它。网络受限时可在联网机器准备依赖wheel后离线安装。

## 配置与新增模型

| 文件 | 作用 |
|---|---|
| configs/model_profiles.yaml | --model 的名称与对应配置映射 |
| configs/sft_qwen3_0_6b.yaml | SFT，输出到 outputs/qwen3_0_6b/sft |
| configs/stage2_qwen3_0_6b.yaml | DPO，自动接上小模型SFT适配器 |
| configs/inference_qwen3_0_6b.yaml | 本地服务配置 |
| configs/download_qwen3_0_6b.yaml | 可选联网下载，仅小模型 |

SFT配置继承 configs/sft_80gb.yaml；想加Qwen3其他尺寸，复制小模型的配置并改 model_repo、base_dir、output_dir、initial_adapter 和 reserve_gib，再在 model_profiles.yaml 添加名称。路径和adapter必须对应同一个模型。

文本Qwen模型使用 model_loader: causal_lm；Qwen3.6-35B-A3B保留 model_loader: image_text。auto按config.json的架构名称选择。只保证实现了这两类加载分支，不承诺任意模型聊天模板和工具协议兼容。

配置示例：

```yaml
_base: configs/sft_qwen3_0_6b.yaml
model_repo: Qwen/Qwen3-1.7B
base_dir: assets/models/Qwen3-1.7B
output_dir: outputs/qwen3_1_7b/sft
reserve_gib: 4
```

保存为 configs/sft_my_model.yaml 后执行：

```text
python run.py sft --config configs/sft_my_model.yaml
```

--config 优先于 --model。新模型需自行创建对应DPO和推理配置；无需改Python加载代码。共享已处理的数据，模型使用各自tokenizer进行tokenization。

此前三个修复已包含：直接读取本地Parquet、用bin(...).count('1')兼容Python3.9、开发模式自动生成本地数据清单。
