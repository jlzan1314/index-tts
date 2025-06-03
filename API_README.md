# IndexTTS API 接口使用说明

这是一个基于 FastAPI 实现的 IndexTTS 语音合成 API 接口，支持文本到语音的转换功能。

## 环境要求

确保已安装 `requirements.txt` 中的所有依赖：

```bash
uv pip install -r requirements.txt
```

## 启动服务

### 方法一：直接启动

```bash
python api.py --host 127.0.0.1 --port 8000
```

### 方法二：使用 Docker 启动

1. 构建并启动 Docker 容器：

```bash
docker-compose up -d --build
```

2. 查看容器日志：

```bash
docker-compose logs -f
```

3. 停止容器：

```bash
docker-compose down
```

### 启动参数说明

- `--host`: API 服务主机地址，默认为 127.0.0.1
- `--port`: API 服务端口，默认为 8000
- `--model_dir`: 模型目录，默认为 checkpoints
- `--no_cuda_kernel`: 不使用 CUDA 内核（如果遇到 CUDA 错误，可以尝试添加此参数）
- `--no_fp16`: 不使用 FP16 精度
- `--device`: 设备，如 cuda:0 或 cpu，默认为 cuda:0
- `--no_cleanup`: 禁用自动清理文件功能
- `--file_max_age`: 文件最大保留时间（秒），默认为3600秒（1小时），设置为0表示立即删除
- `--cleanup_interval`: 清理间隔（秒），默认为3600秒（1小时）

## API 接口说明

### 1. JSON 请求方式 - 使用默认参考音频

**接口**: `/tts/json`

**方法**: POST

**请求体**:
```json
{
  "text": "要转换为语音的文本内容"
}
```

**示例**:
```bash
curl -X POST "http://127.0.0.1:8000/tts/json" \
     -H "Content-Type: application/json" \
     -d '{"text":"大家好，这是一个语音合成测试"}' \
     --output output.wav
```

### 2. 表单请求方式 - 支持自定义参考音频

**接口**: `/tts/form`

**方法**: POST

**参数**:
- `text`: 要转换为语音的文本内容 (表单字段)
- `wav_file`: 可选的参考音频文件 (文件上传)

**示例**:
```bash
curl -X POST "http://127.0.0.1:8000/tts/form" \
     -F "text=大家好，这是一个语音合成测试" \
     -F "wav_file=@/path/to/reference.wav" \
     --output output.wav
```

### 3. 健康检查接口

**接口**: `/health`

**方法**: GET

**示例**:
```bash
curl "http://127.0.0.1:8000/health"
```

**返回示例**:
```json
{
  "status": "ok",
  "model_loaded": true,
  "cleanup_enabled": true,
  "file_max_age": 3600,
  "cleanup_interval": 3600
}
```

### 4. 手动触发文件清理接口

**接口**: `/cleanup`

**方法**: POST

**示例**:
```bash
curl -X POST "http://127.0.0.1:8000/cleanup"
```

**返回示例**:
```json
{
  "status": "success",
  "files_removed": 5,
  "files_remaining": 2
}
```

## 使用 Python 调用示例

```python
import requests

# JSON 方式调用
def tts_json(text, output_file="output.wav"):
    response = requests.post(
        "http://127.0.0.1:8000/tts/json",
        json={"text": text}
    )
    
    if response.status_code == 200:
        with open(output_file, "wb") as f:
            f.write(response.content)
        print(f"语音已保存到 {output_file}")
    else:
        print(f"请求失败: {response.text}")

# 表单方式调用（带参考音频）
def tts_form(text, reference_wav=None, output_file="output.wav"):
    data = {"text": text}
    files = {}
    
    if reference_wav:
        files = {"wav_file": open(reference_wav, "rb")}
    
    response = requests.post(
        "http://127.0.0.1:8000/tts/form",
        data=data,
        files=files
    )
    
    if response.status_code == 200:
        with open(output_file, "wb") as f:
            f.write(response.content)
        print(f"语音已保存到 {output_file}")
    else:
        print(f"请求失败: {response.text}")
    
    if reference_wav and "wav_file" in files:
        files["wav_file"].close()

# 示例调用
tts_json("这是一个测试文本", "json_output.wav")
tts_form("这是另一个测试文本", "test_data/input.wav", "form_output.wav")
```

## Docker 部署说明

### 目录结构

```
.
├── Dockerfile          # Docker 构建文件
├── docker-compose.yml  # Docker Compose 配置文件
├── api.py              # FastAPI 应用程序
├── checkpoints/        # 模型目录（需要挂载）
└── outputs/            # 输出目录（会被挂载）
```

### 环境变量配置

在 `docker-compose.yml` 中可以配置以下环境变量：

- `HOST`: API 服务主机地址，默认为 0.0.0.0
- `PORT`: API 服务端口，默认为 8000
- `MODEL_DIR`: 模型目录，默认为 /app/checkpoints
- `CLEANUP_ENABLED`: 是否启用自动清理功能，默认为 true
- `FILE_MAX_AGE`: 文件最大保留时间（秒），默认为 3600
- `CLEANUP_INTERVAL`: 清理间隔（秒），默认为 3600
- `TORCH_USE_CUDA_DSA`: 设置为 1 可以启用 CUDA DSA 调试
- `CUDA_LAUNCH_BLOCKING`: 设置为 1 可以帮助定位 CUDA 错误

### 挂载卷

- `./checkpoints:/app/checkpoints`: 挂载模型目录
- `./outputs:/app/outputs`: 挂载输出目录

## 注意事项

1. 首次调用 API 时，模型加载可能需要一些时间
2. 生成的音频文件会保存在 `outputs/api` 目录下
3. 如果遇到 CUDA 相关错误，可以尝试添加 `--no_cuda_kernel` 参数启动服务
4. 对于长文本，生成过程可能需要较长时间
5. 在 Docker 环境中，确保 NVIDIA Container Toolkit 已正确安装，以支持 GPU 加速
6. 系统默认启用自动文件清理功能，会定期删除超过指定时间的音频文件
7. 可以通过 `--file_max_age` 参数设置文件保留时间，设置为0表示立即删除
8. 如需禁用自动清理功能，可以添加 `--no_cleanup` 参数启动服务