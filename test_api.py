import os
import requests
import argparse

def test_tts_json(text, output_file="json_output.wav", api_url="http://127.0.0.1:8000/tts/json"):
    """
    使用JSON方式测试TTS API
    """
    print(f"正在使用JSON方式合成文本: {text}")
    response = requests.post(
        api_url,
        json={"text": text}
    )
    
    if response.status_code == 200:
        with open(output_file, "wb") as f:
            f.write(response.content)
        print(f"语音已保存到 {output_file}")
        return True
    else:
        print(f"请求失败: {response.status_code} - {response.text}")
        return False

def test_tts_form(text, reference_wav=None, output_file="form_output.wav", api_url="http://127.0.0.1:8000/tts/form"):
    """
    使用表单方式测试TTS API，可选择提供参考音频
    """
    data = {"text": text}
    files = {}
    
    if reference_wav and os.path.exists(reference_wav):
        files = {"wav_file": open(reference_wav, "rb")}
        print(f"正在使用表单方式合成文本: {text}，参考音频: {reference_wav}")
    else:
        print(f"正在使用表单方式合成文本: {text}，使用默认参考音频")
    
    try:
        response = requests.post(
            api_url,
            data=data,
            files=files
        )
        
        if response.status_code == 200:
            with open(output_file, "wb") as f:
                f.write(response.content)
            print(f"语音已保存到 {output_file}")
            return True
        else:
            print(f"请求失败: {response.status_code} - {response.text}")
            return False
    finally:
        # 确保文件被关闭
        if reference_wav and "wav_file" in files:
            files["wav_file"].close()

def test_health(api_url="http://127.0.0.1:8000/health"):
    """
    测试健康检查接口
    """
    print("正在检查API服务健康状态...")
    try:
        response = requests.get(api_url)
        if response.status_code == 200:
            print(f"API服务正常: {response.json()}")
            return True
        else:
            print(f"API服务异常: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"无法连接到API服务: {e}")
        return False

# 测试文件清理接口
def test_cleanup(api_host, api_port):
    url = f"http://{api_host}:{api_port}/cleanup"
    try:
        response = requests.post(url)
        if response.status_code == 200:
            print("文件清理成功:", response.json())
            return True
        else:
            print(f"文件清理失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"文件清理异常: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="测试IndexTTS API接口")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="API服务主机地址")
    parser.add_argument("--port", type=int, default=8000, help="API服务端口")
    parser.add_argument("--text", type=str, default="这是一个测试文本，用于验证语音合成API接口。", help="要合成的文本")
    parser.add_argument("--reference", type=str, default="test_data/input.wav", help="参考音频文件路径")
    parser.add_argument("--output_dir", type=str, default="outputs/api_test", help="输出目录")
    parser.add_argument("--test_cleanup", action="store_true", help="测试文件清理接口")
    
    args = parser.parse_args()
    
    # 创建输出目录
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 构建API URL
    base_url = f"http://{args.host}:{args.port}"
    
    # 测试健康检查
    if not test_health(f"{base_url}/health"):
        print("API服务不可用，请确保服务已启动")
        return
    
    # 测试JSON方式
    json_output = os.path.join(args.output_dir, "json_output.wav")
    test_tts_json(args.text, json_output, f"{base_url}/tts/json")
    
    # 测试表单方式（使用默认参考音频）
    form_output1 = os.path.join(args.output_dir, "form_output_default.wav")
    test_tts_form(args.text, None, form_output1, f"{base_url}/tts/form")
    
    # 测试表单方式（使用自定义参考音频）
    if os.path.exists(args.reference):
        form_output2 = os.path.join(args.output_dir, "form_output_custom.wav")
        test_tts_form(args.text, args.reference, form_output2, f"{base_url}/tts/form")
    else:
        print(f"参考音频文件 {args.reference} 不存在，跳过自定义参考音频测试")
    
    # 测试文件清理接口
    if args.test_cleanup:
        print("\n测试文件清理接口...")
        test_cleanup(args.host, args.port)
    
    print("\n测试完成，请检查输出文件")

if __name__ == "__main__":
    main()