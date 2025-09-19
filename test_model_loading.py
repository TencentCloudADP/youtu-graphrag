#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试模型加载功能的脚本
用于验证sentence-transformers/all-MiniLM-L6-v2模型是否能正确加载
"""
import os
import sys
import torch
from sentence_transformers import SentenceTransformer


def test_model_loading():
    """测试模型加载功能"""
    print("===== 测试模型加载功能 =====")
    
    # 打印Python和库版本信息
    print(f"Python版本: {sys.version}")
    print(f"PyTorch版本: {torch.__version__}")
    
    # 检查环境变量
    hf_endpoint = os.environ.get('HF_ENDPOINT', '未设置')
    print(f"HF_ENDPOINT环境变量: {hf_endpoint}")
    
    # 测试直接从HuggingFace加载模型
    print("\n尝试直接从HuggingFace加载模型...")
    try:
        # 强制使用环境变量中设置的HF_ENDPOINT
        original_hf_endpoint = os.environ.get('HF_ENDPOINT')
        os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'  # 设置为镜像站点
        
        model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        print("✅ 成功加载模型！")
        
        # 测试模型推理
        print("\n测试模型推理功能...")
        sentences = ["这是一个测试句子", "This is a test sentence"]
        embeddings = model.encode(sentences)
        print(f"✅ 成功生成嵌入向量！向量维度: {embeddings.shape}")
        
        # 恢复原始环境变量
        if original_hf_endpoint is not None:
            os.environ['HF_ENDPOINT'] = original_hf_endpoint
        
    except Exception as e:
        print(f"❌ 模型加载失败: {e}")
        print("\n尝试从本地缓存加载模型...")
        try:
            # 尝试直接使用本地缓存路径
            cache_path = os.path.expanduser("~/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2")
            print(f"使用本地缓存路径: {cache_path}")
            
            # 找到snapshots目录
            snapshots = [d for d in os.listdir(cache_path) if os.path.isdir(os.path.join(cache_path, d)) and not d.startswith('.')]
            if snapshots:
                snapshot_path = os.path.join(cache_path, snapshots[0])
                print(f"找到snapshot目录: {snapshot_path}")
                model = SentenceTransformer(snapshot_path)
                print("✅ 成功从本地缓存加载模型！")
                
                # 测试模型推理
                sentences = ["这是一个测试句子", "This is a test sentence"]
                embeddings = model.encode(sentences)
                print(f"✅ 成功生成嵌入向量！向量维度: {embeddings.shape}")
            else:
                print("❌ 未在本地缓存中找到snapshot目录")
        except Exception as inner_e:
            print(f"❌ 从本地缓存加载模型失败: {inner_e}")
    
    print("\n===== 测试完成 =====")


if __name__ == "__main__":
    test_model_loading()