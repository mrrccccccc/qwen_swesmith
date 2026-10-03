# Windows / Linux 最短启动说明

安装 Python 3.12，解压后在项目根目录打开终端。

Windows CMD / PowerShell：
```text
py -3.12 setup_env.py --cuda cu128
```

Linux：
```text
python3.12 setup_env.py --cuda cu128
```

之后两系统均执行：
```text
python run.py download
python run.py licenses
python run.py prepare
python run.py sft --model qwen3-0.6b
python run.py stage2 --model qwen3-0.6b
python run.py curves --run-dir outputs/qwen3_0_6b/sft
python run.py curves --run-dir outputs/qwen3_0_6b/stage2
```

Windows没有python命令时，把python换成py即可。
入口自动使用项目虚拟环境，不用activate，不需要任何.sh脚本。
下载后训练和推理全部本地加载。

本地文本推理：
```text
python run.py serve --adapter outputs/stage2/best_adapter
```

默认是开发模式，不因未填的benchmark manifest阻塞；正式面试实验使用formal
配置并先冻结评测版本，完整流程在README。

24GB不能运行本项目BF16的35B基座；80GB是短窗口候选，H200 141GB更有余量。
原生Windows不支持官方vLLM CUDA后端，完整长上下文及官方容器评测需要Linux/
WSL2或Linux服务器。按要求，本次只修改代码和打包，没有运行验证。
