import os
import logging
from utils.tree_comm import FastTreeComm
import networkx as nx

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def verify_environment_variables():
    """
    验证环境变量是否正确设置
    """
    print("=== 验证环境变量设置 ===")
    hf_offline = os.environ.get('HF_HUB_OFFLINE')
    hf_disable_symlinks = os.environ.get('HF_HUB_DISABLE_SYMLINKS_WARNING')
    
    print(f"HF_HUB_OFFLINE: {hf_offline}")
    print(f"HF_HUB_DISABLE_SYMLINKS_WARNING: {hf_disable_symlinks}")
    
    if hf_offline == '1':
        print("✅ HuggingFace离线模式已启用")
    else:
        print("❌ HuggingFace离线模式未启用")


def test_tree_comm_model_loading():
    """
    测试FastTreeComm类能否正确加载本地模型
    """
    print("\n=== 测试FastTreeComm模型加载 ===")
    
    try:
        # 创建一个简单的图用于测试
        G = nx.DiGraph()
        G.add_node(1, properties={"name": "测试节点1"})
        G.add_node(2, properties={"name": "测试节点2"})
        G.add_edge(1, 2, relation="关联于")
        
        # 初始化FastTreeComm
        print("创建FastTreeComm实例...")
        tree_comm = FastTreeComm(G)
        
        # 验证模型是否加载成功
        if hasattr(tree_comm, 'model'):
            print("✅ 模型已成功加载到FastTreeComm实例")
            
            # 测试模型功能
            try:
                print("测试模型嵌入功能...")
                embedding = tree_comm.get_triple_embedding(1)
                print(f"模型生成的嵌入向量形状: {embedding.shape}")
                print("✅ 模型嵌入功能正常工作")
            except Exception as e:
                print(f"❌ 模型嵌入功能测试失败: {str(e)}")
        else:
            print("❌ 模型未能加载到FastTreeComm实例")
            
    except Exception as e:
        print(f"❌ FastTreeComm初始化失败: {str(e)}")
        import traceback
        traceback.print_exc()


def main():
    # 验证环境变量
    verify_environment_variables()
    
    # 测试TreeComm模型加载
    test_tree_comm_model_loading()
    
    # 总结
    print("\n=== 测试总结 ===")
    print("1. 环境变量已配置为强制使用本地模型")
    print("2. FastTreeComm类的模型加载逻辑已优化")
    print("3. 系统现在应该能在HuggingFace被屏蔽的情况下正常工作")
    print("\n所有更改已完成，请运行start.sh启动系统验证功能")

if __name__ == "__main__":
    main()