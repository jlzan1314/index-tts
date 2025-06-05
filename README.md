# 当前对比其他tts
主要看重的是实时性，输出较快，还有中文支持较好，腾讯出品

官方git仓库在：
https://github.com/index-tts/index-tts

# 环境
- 系统： wsl2 中的ubuntu 20.04
- 显卡： NVIDIA GeForce RTX 5090 D
- python： 3.10

huggingface.co github.com 需要魔法访问
# 安装步骤：

## 1.在环境中手动启动

和官方文档不太一样减少依赖和支持50系的pytorch：

如果系统中没有ffmpeg 及python3需要安装
```bash
sed -i 's/archive.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list && \
sed -i 's/security.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list && \
apt-get update && apt-get install -y \
curl \
python3 \
python3-pip \
ffmpeg
```

```bash
git clone https://github.com/jlzan1314/index-tts.git
cd index-tts
python venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 如果不是50系显卡，这两步不用安装
pip uninstall -y torch torchvision torchaudio
pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128

# 下载模型
wget https://huggingface.co/IndexTeam/IndexTTS-1.5/resolve/main/bigvgan_discriminator.pth -P checkpoints
wget https://huggingface.co/IndexTeam/IndexTTS-1.5/resolve/main/bigvgan_generator.pth -P checkpoints
wget https://huggingface.co/IndexTeam/IndexTTS-1.5/resolve/main/bpe.model -P checkpoints
wget https://huggingface.co/IndexTeam/IndexTTS-1.5/resolve/main/dvae.pth -P checkpoints
wget https://huggingface.co/IndexTeam/IndexTTS-1.5/resolve/main/gpt.pth -P checkpoints
wget https://huggingface.co/IndexTeam/IndexTTS-1.5/resolve/main/unigram_12000.vocab -P checkpoints
wget https://huggingface.co/IndexTeam/IndexTTS-1.5/resolve/main/config.yaml -P checkpoints

#启动
python api.py

#测试验证，另起一个shell,hello.wav是音频
curl http://127.0.0.1:8010/tts/gen?text=hello --output hello.wav
```

## 使用docker启动
如果有环境中有docker的话，可以直接docker启动
1. 先下载checkpoints模型：

```bash
wget https://huggingface.co/IndexTeam/IndexTTS-1.5/resolve/main/bigvgan_discriminator.pth -P checkpoints
wget https://huggingface.co/IndexTeam/IndexTTS-1.5/resolve/main/bigvgan_generator.pth -P checkpoints
wget https://huggingface.co/IndexTeam/IndexTTS-1.5/resolve/main/bpe.model -P checkpoints
wget https://huggingface.co/IndexTeam/IndexTTS-1.5/resolve/main/dvae.pth -P checkpoints
wget https://huggingface.co/IndexTeam/IndexTTS-1.5/resolve/main/gpt.pth -P checkpoints
wget https://huggingface.co/IndexTeam/IndexTTS-1.5/resolve/main/unigram_12000.vocab -P checkpoints
wget https://huggingface.co/IndexTeam/IndexTTS-1.5/resolve/main/config.yaml -P checkpoints
```

2 .启动并build镜像
会占用 8010端口
```
docker compose up --build
```

#测试验证，hello.wav是音频
```
curl http://127.0.0.1:8010/tts/gen?text=hello --output hello.wav
```