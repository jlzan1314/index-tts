import os
import sys
import tempfile
import uuid
import time
import glob
import threading
import datetime
from typing import Optional

import torchaudio
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn

# 添加当前目录到系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, "indextts"))

from indextts.infer import IndexTTS
from contextlib import asynccontextmanager

# 创建输出目录
os.makedirs("outputs/api", exist_ok=True)

# 文件清理配置
CLEANUP_INTERVAL = int(os.environ.get("CLEANUP_INTERVAL", 300))  # 清理间隔（秒）
FILE_MAX_AGE = int(os.environ.get("FILE_MAX_AGE", 300))  # 文件最大保留时间（秒）
CLEANUP_ENABLED = os.environ.get("CLEANUP_ENABLED", "true").lower() in ("true", "1", "yes")  # 是否启用自动清理
OUTPUT_DIR = "outputs/api"  # 输出目录

# 清理过期文件
def cleanup_old_files():
    """清理过期的音频文件"""
    if not CLEANUP_ENABLED:
        return
        
    try:
        current_time = time.time()
        pattern = os.path.join(OUTPUT_DIR, "tts_*.wav")
        for file_path in glob.glob(pattern):
            # 检查文件修改时间
            file_mod_time = os.path.getmtime(file_path)
            if current_time - file_mod_time > FILE_MAX_AGE:
                try:
                    os.remove(file_path)
                    print(f"已清理过期文件: {file_path}")
                except Exception as e:
                    print(f"清理文件失败 {file_path}: {e}")
    except Exception as e:
        print(f"文件清理过程出错: {e}")

# 后台清理任务
def background_cleanup():
    """后台定期清理任务"""
    while CLEANUP_ENABLED:
        cleanup_old_files()
        time.sleep(CLEANUP_INTERVAL)

# 启动后台清理线程
cleanup_thread = None

# 全局TTS模型实例
tts = None

# 模型初始化函数
def init_model(model_dir="checkpoints", use_cuda_kernel=True, is_fp16=True, device="cuda:0"):
    global tts
    if tts is None:
        try:
            tts = IndexTTS(
                model_dir=model_dir,
                cfg_path=os.path.join(model_dir, "config.yaml"),
                use_cuda_kernel=use_cuda_kernel,
                is_fp16=is_fp16,
                device=device
            )
            print(">> TTS模型已成功加载")
        except Exception as e:
            print(f">> TTS模型加载失败: {e}")
            raise e
    return tts

# 启动时初始化模型和清理线程，关闭时停止清理线程
@asynccontextmanager
async def lifespan(app: FastAPI):
    global cleanup_thread
    
    try:
        # 初始化模型
        init_model()
        
        # 启动清理线程
        if CLEANUP_ENABLED and cleanup_thread is None:
            cleanup_thread = threading.Thread(target=background_cleanup, daemon=True)
            cleanup_thread.start()
            print(f">> 文件自动清理已启动，间隔: {CLEANUP_INTERVAL}秒，文件最大保留时间: {FILE_MAX_AGE}秒")
    except Exception as e:
        print(f"启动时初始化失败: {e}")
    
    yield
    
    # 停止清理线程
    CLEANUP_ENABLED = False
    if cleanup_thread and cleanup_thread.is_alive():
        try:
            cleanup_thread.join(timeout=2.0)  # 等待线程结束，最多2秒
            print(">> 清理线程已停止")
        except Exception as e:
            print(f">> 停止清理线程时出错: {e}")
    
    print(">> API服务已关闭")

# 创建FastAPI应用
app = FastAPI(
    title="IndexTTS API",
    description="语音合成API接口，基于IndexTTS模型",
    version="1.0.0",
    lifespan=lifespan
)

# 请求模型
class TTSRequest(BaseModel):
    text: str
    
# 文本转语音接口 - JSON请求方式
@app.post("/tts/json")
async def text_to_speech_json(request: TTSRequest, background_tasks: BackgroundTasks):
    if tts is None:
        raise HTTPException(status_code=500, detail="TTS模型未初始化")
    
    try:
        # 生成唯一文件名
        output_filename = f"outputs/api/tts_{uuid.uuid4()}.wav"
        
        # 使用默认参考音频
        audio_prompt = "test_data/input.wav"
        
        # 生成语音
        output_path = tts.infer(
            audio_prompt=audio_prompt,
            text=request.text,
            output_path=output_filename,
            verbose=False
        )
        
        # 添加后台任务，在响应发送后删除文件（可选，根据配置决定）
        if CLEANUP_ENABLED and FILE_MAX_AGE <= 0:
            background_tasks.add_task(lambda: os.unlink(output_path) if os.path.exists(output_path) else None)
        
        # 返回生成的音频文件
        return FileResponse(
            path=output_path,
            media_type="audio/wav",
            filename=os.path.basename(output_path)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"语音合成失败: {str(e)}")

# 文本转语音接口 - 表单请求方式，支持自定义参考音频
@app.post("/tts/form")
async def text_to_speech_form(
    background_tasks: BackgroundTasks,
    text: str = Form(...),
    wav_file: Optional[UploadFile] = File(None)
):
    if tts is None:
        raise HTTPException(status_code=500, detail="TTS模型未初始化")
    
    try:
        # 生成唯一文件名
        output_filename = f"outputs/api/tts_{uuid.uuid4()}.wav"
        
        # 处理上传的参考音频文件
        audio_prompt = "test_data/input.wav"  # 默认参考音频
        if wav_file is not None:
            # 保存上传的音频到临时文件
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            temp_file.close()
            
            # 写入上传的音频数据
            with open(temp_file.name, "wb") as f:
                f.write(await wav_file.read())
            
            audio_prompt = temp_file.name
        
        # 生成语音
        output_path = tts.infer(
            audio_prompt=audio_prompt,
            text=text,
            output_path=output_filename,
            verbose=False
        )
        
        # 如果使用了临时文件，清理它
        if wav_file is not None:
            os.unlink(audio_prompt)
        
        # 添加后台任务，在响应发送后删除文件（可选，根据配置决定）
        if CLEANUP_ENABLED and FILE_MAX_AGE <= 0:
            background_tasks.add_task(lambda: os.unlink(output_path) if os.path.exists(output_path) else None)
        
        # 返回生成的音频文件
        return FileResponse(
            path=output_path,
            media_type="audio/wav",
            filename=os.path.basename(output_path)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"语音合成失败: {str(e)}")

# 健康检查接口
@app.get("/health")
async def health_check():
    return {
        "status": "ok", 
        "model_loaded": tts is not None,
        "cleanup_enabled": CLEANUP_ENABLED,
        "file_max_age": FILE_MAX_AGE,
        "cleanup_interval": CLEANUP_INTERVAL
    }

# 手动触发文件清理接口
@app.post("/cleanup")
async def manual_cleanup():
    try:
        files_before = len(glob.glob(os.path.join(OUTPUT_DIR, "tts_*.wav")))
        cleanup_old_files()
        files_after = len(glob.glob(os.path.join(OUTPUT_DIR, "tts_*.wav")))
        return {
            "status": "success",
            "files_removed": files_before - files_after,
            "files_remaining": files_after
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")

# 主函数
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="IndexTTS API Server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="API服务主机地址")
    parser.add_argument("--port", type=int, default=8000, help="API服务端口")
    parser.add_argument("--model_dir", type=str, default="checkpoints", help="模型目录")
    parser.add_argument("--no_cuda_kernel", action="store_true", help="不使用CUDA内核")
    parser.add_argument("--no_fp16", action="store_true", help="不使用FP16精度")
    parser.add_argument("--device", type=str, default="cuda:0", help="设备，如cuda:0或cpu")
    parser.add_argument("--no_cleanup", action="store_true", help="禁用自动清理文件")
    parser.add_argument("--file_max_age", type=int, default=3600, help="文件最大保留时间（秒），0表示立即删除")
    parser.add_argument("--cleanup_interval", type=int, default=3600, help="清理间隔（秒）")
    
    args = parser.parse_args()
    
    # 更新文件清理配置
    # 直接修改全局变量，不需要global声明
    CLEANUP_ENABLED = not args.no_cleanup
    FILE_MAX_AGE = args.file_max_age
    CLEANUP_INTERVAL = args.cleanup_interval
    
    # 初始化模型
    try:
        init_model(
            model_dir=args.model_dir,
            use_cuda_kernel=not args.no_cuda_kernel,
            is_fp16=not args.no_fp16,
            device=args.device
        )
    except Exception as e:
        print(f"模型初始化失败: {e}")
        sys.exit(1)
    
    # 启动服务器
    uvicorn.run(
        "api:app",
        host=args.host,
        port=args.port,
        reload=False
    )