#!/usr/bin/env python3
import json
import sys
sys.path.append('.')

print('=== 分析构建结果 ===')

# 1. 检查生成的图谱文件
try:
    with open('output/graphs/building_assets_new.json', 'r', encoding='utf-8') as f:
        graph_data = json.load(f)
    
    print(f'✅ 图谱文件生成成功')
    print(f'📊 图谱包含 {len(graph_data)} 个关系')
    
    # 显示前几个关系
    print(f'🔗 示例关系:')
    for i, rel in enumerate(graph_data[:3]):
        start_node = rel.get('start_node', {}).get('label', 'Unknown')
        relation = rel.get('relation', 'Unknown')
        end_node = rel.get('end_node', {}).get('label', 'Unknown')
        print(f'  {i+1}. {start_node} --[{relation}]--> {end_node}')
        
except Exception as e:
    print(f'❌ 图谱文件检查失败: {e}')

print()

# 2. 检查chunk文件
try:
    with open('output/chunks/building_assets.txt', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f'✅ Chunk文件包含 {len(lines)} 行')
    
    # 统计每个文档的chunk数量
    chunk_count = {}
    for line in lines:
        if 'assets.xlsx' in line:
            chunk_count['assets.xlsx'] = chunk_count.get('assets.xlsx', 0) + 1
        elif 'Space.xlsx' in line:
            chunk_count['Space.xlsx'] = chunk_count.get('Space.xlsx', 0) + 1
        elif 'systems.xlsx' in line:
            chunk_count['systems.xlsx'] = chunk_count.get('systems.xlsx', 0) + 1
    
    print('📊 各文档chunk数量:')
    for doc, count in chunk_count.items():
        print(f'  {doc}: {count} chunks')
        
except Exception as e:
    print(f'❌ Chunk文件检查失败: {e}')

print()

# 3. 分析可能的失败原因
print('🔍 失败原因分析:')
print('可能的原因:')
print('1. Space.xlsx或systems.xlsx中的某些chunk可能包含特殊字符')
print('2. qwen2:0.5b模型对复杂内容的处理能力有限')
print('3. 某些chunk的内容格式可能导致解析失败')
print()
print('💡 建议:')
print('1. 虽然有2个文档失败，但1个文档成功处理并生成了完整图谱')
print('2. 可以检查生成的图谱质量，如果满足需求就可以使用')
print('3. 如果需要处理失败的文档，可以尝试使用更大的模型如qwen2:7b')
