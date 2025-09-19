import os
import glob
from sentence_transformers import SentenceTransformer
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_model_paths():
    """
    检查本地是否存在all-MiniLM-L6-v2模型及其可能的路径
    """
    # 定义可能的模型路径
    model_name = "all-MiniLM-L6-v2"
    possible_paths = [
        os.path.join(".cache", "huggingface", "hub"),
        os.path.expanduser("~/.cache/huggingface/hub"),
        os.path.expanduser(f"~/.cache/huggingface/hub/models--sentence-transformers--{model_name}/snapshots/")
    ]
    
    print("=== 检查本地模型路径 ===")
    found_paths = []
    for path in possible_paths:
        if os.path.exists(path):
            print(f"找到路径: {path}")
            # 查找模型文件
            if os.path.isdir(path):
                model_glob = os.path.join(path, "*")
                model_files = glob.glob(model_glob)
                if model_files:
                    print(f"  包含文件/目录: {len(model_files)} 个")
                    # 检查是否有模型配置文件
                    for root, dirs, files in os.walk(path):
                        if "config.json" in files or "pytorch_model.bin" in files:
                            found_paths.append(root)
                            print(f"  找到可能的模型目录: {root}")
    
    return found_paths

def try_load_model():
    """
    尝试加载本地模型，避免从Hugging Face下载
    """
    model_name = "all-MiniLM-L6-v2"
    
    print("\n=== 尝试加载本地模型 ===")
    
    # 1. 尝试直接使用已知的snapshot路径
    snapshot_glob = os.path.expanduser(f"~/.cache/huggingface/hub/models--sentence-transformers--{model_name}/snapshots/*")
    snapshot_paths = glob.glob(snapshot_glob)
    
    if snapshot_paths:
        print(f"找到{snapshot_paths[0]} 作为可能的模型路径")
        try:
            print(f"尝试从绝对路径加载模型: {snapshot_paths[0]}")
            model = SentenceTransformer(snapshot_paths[0])
            print("✅ 成功从绝对路径加载模型!")
            # 测试模型
            test_embedding(model)
            return model
        except Exception as e:
            print(f"❌ 从绝对路径加载失败: {str(e)}")
    
    # 2. 尝试使用自定义缓存路径
    cache_paths = [".cache", os.path.expanduser("~/.cache/huggingface/hub")]
    for cache_path in cache_paths:
        try:
            print(f"尝试使用缓存路径: {cache_path}")
            model = SentenceTransformer(model_name, cache_folder=cache_path, local_files_only=True)
            print(f"✅ 成功从缓存路径加载模型!")
            # 测试模型
            test_embedding(model)
            return model
        except Exception as e:
            print(f"❌ 从缓存路径加载失败: {str(e)}")
    
    # 3. 最后尝试不指定路径，但设置local_files_only=True
    try:
        print("尝试设置local_files_only=True加载模型")
        model = SentenceTransformer(model_name, local_files_only=True)
        print("✅ 成功加载模型!")
        # 测试模型
        test_embedding(model)
        return model
    except Exception as e:
        print(f"❌ 所有加载尝试均失败: {str(e)}")
        print("请确保模型已正确下载到本地目录")
    
    return None

def test_embedding(model):
    """
    测试模型是否能正常生成嵌入向量
    """
    try:
        sentences = ["这是一个测试句子", "This is a test sentence"]
        embeddings = model.encode(sentences)
        print(f"模型生成的嵌入向量形状: {embeddings.shape}")
        print("嵌入向量示例:", embeddings[0][:5])
    except Exception as e:
        print(f"测试嵌入向量失败: {str(e)}")

def suggest_improvements():
    """
    基于测试结果提供改进建议
    """
    print("\n=== 配置改进建议 ===")
    print("1. 在utils/tree_comm.py中，FastTreeComm类的__init__方法可以添加local_files_only=True参数")
    print("2. 确保环境变量设置正确，避免从Hugging Face下载：")
    print("   HF_HUB_OFFLINE=1\n   HF_HUB_DISABLE_SYMLINKS_WARNING=1")
    print("3. 可以在.env文件中添加这些环境变量，以便系统启动时自动加载")

def main():
    # 检查模型路径
    found_paths = check_model_paths()
    
    # 尝试加载模型
    model = try_load_model()
    
    # 提供改进建议
    suggest_improvements()
    
    # 生成一个优化后的模型加载代码段供参考
    print("\n=== 优化后的模型加载代码示例 ===")
    optimized_code = '''# 优化后的模型加载逻辑
try:
    # 1. 尝试直接使用本地模型绝对路径
    import glob
    model_glob = os.path.expanduser("~/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/snapshots/*")
    model_paths = glob.glob(model_glob)
    if model_paths:
        self.model = SentenceTransformer(model_paths[0], local_files_only=True)
        logger.info(f"Successfully loaded model from absolute path: {model_paths[0]}")
    else:
        # 2. 尝试使用自定义缓存路径
        cache_path = os.path.expanduser("~/.cache/huggingface/hub")
        self.model = SentenceTransformer("all-MiniLM-L6-v2", 
                                         cache_folder=cache_path, 
                                         local_files_only=True)
        logger.info(f"Successfully loaded model from cache path: {cache_path}")
except Exception as e:
    logger.error(f"Failed to load model: {str(e)}")
    # 可以添加备用方案或抛出更明确的错误信息
'''    
    print(optimized_code)

if __name__ == "__main__":
    main()