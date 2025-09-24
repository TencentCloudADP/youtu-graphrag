"""
查询增强器：提升检索系统对建筑资产查询的理解能力
"""
import re
from typing import List, Dict, Any

class QueryEnhancer:
    """查询增强器，专门用于建筑资产查询的语义增强"""
    
    def __init__(self):
        # 楼层同义词映射
        self.floor_synonyms = {
            "3F": ["3层", "三层", "3F层"],
            "3层": ["3F", "三层", "3F层"],
            "三层": ["3F", "3层", "3F层"],
            "2F": ["2层", "二层", "2F层"],
            "2层": ["2F", "二层", "2F层"],
            "二层": ["2F", "2层", "2F层"],
            "1F": ["1层", "一层", "1F层"],
            "1层": ["1F", "一层", "1F层"],
            "一层": ["1F", "1层", "1F层"],
            "B1": ["B1层", "地下一层", "地下1层"],
            "地下一层": ["B1", "B1层", "地下1层"],
        }
        
        # 设备类型同义词
        self.equipment_synonyms = {
            "设备": ["空调箱", "配电箱", "变风量末端", "冷机", "水泵", "配电柜"],
            "空调设备": ["空调箱", "变风量末端", "VAV"],
            "电气设备": ["配电箱", "配电柜", "开关柜"],
            "HVAC设备": ["空调箱", "冷机", "水泵", "变风量末端"],
        }
        
        # 建筑同义词
        self.building_synonyms = {
            "A栋": ["A座", "A建筑", "A楼"],
            "B栋": ["B座", "B建筑", "B楼"],
        }
    
    def enhance_query(self, query: str) -> Dict[str, Any]:
        """
        增强查询，返回增强后的查询信息
        
        Args:
            query: 原始查询
            
        Returns:
            {
                "original_query": 原始查询,
                "enhanced_queries": 增强查询列表,
                "extracted_entities": 提取的实体,
                "query_type": 查询类型
            }
        """
        result = {
            "original_query": query,
            "enhanced_queries": [],
            "extracted_entities": {},
            "query_type": self._classify_query(query)
        }
        
        # 提取实体
        result["extracted_entities"] = self._extract_entities(query)
        
        # 生成增强查询
        result["enhanced_queries"] = self._generate_enhanced_queries(query, result["extracted_entities"])
        
        return result
    
    def _classify_query(self, query: str) -> str:
        """分类查询类型"""
        if "设备" in query or "空调" in query or "配电" in query:
            if "有哪些" in query or "清单" in query or "列表" in query:
                return "equipment_list"
            else:
                return "equipment_info"
        elif "位置" in query or "在哪" in query:
            return "location_query"
        elif "系统" in query:
            return "system_query"
        else:
            return "general"
    
    def _extract_entities(self, query: str) -> Dict[str, List[str]]:
        """从查询中提取实体"""
        entities = {
            "buildings": [],
            "floors": [],
            "equipment_types": [],
            "locations": []
        }
        
        # 提取建筑
        for building in ["A栋", "B栋", "A座", "B座"]:
            if building in query:
                entities["buildings"].append(building)
        
        # 提取楼层
        floor_patterns = [
            r"(\d+F)",
            r"(\d+层)",
            r"([一二三四五六七八九十]+层)",
            r"(地下[一二三四五六七八九十\d]+层?)",
            r"(B\d+)"
        ]
        
        for pattern in floor_patterns:
            matches = re.findall(pattern, query)
            entities["floors"].extend(matches)
        
        # 提取设备类型
        equipment_keywords = ["设备", "空调箱", "配电箱", "变风量", "冷机", "水泵", "配电柜"]
        for keyword in equipment_keywords:
            if keyword in query:
                entities["equipment_types"].append(keyword)
        
        return entities
    
    def _generate_enhanced_queries(self, original_query: str, entities: Dict[str, List[str]]) -> List[str]:
        """生成增强查询"""
        enhanced_queries = [original_query]
        
        # 楼层同义词扩展
        for floor in entities["floors"]:
            if floor in self.floor_synonyms:
                for synonym in self.floor_synonyms[floor]:
                    enhanced_query = original_query.replace(floor, synonym)
                    if enhanced_query != original_query:
                        enhanced_queries.append(enhanced_query)
        
        # 设备类型扩展
        for eq_type in entities["equipment_types"]:
            if eq_type in self.equipment_synonyms:
                for synonym in self.equipment_synonyms[eq_type]:
                    enhanced_query = original_query.replace(eq_type, synonym)
                    if enhanced_query != original_query:
                        enhanced_queries.append(enhanced_query)
        
        # 生成位置编码查询
        enhanced_queries.extend(self._generate_location_code_queries(entities))
        
        return list(set(enhanced_queries))  # 去重
    
    def _generate_location_code_queries(self, entities: Dict[str, List[str]]) -> List[str]:
        """生成基于位置编码的查询"""
        location_queries = []
        
        for building in entities["buildings"]:
            for floor in entities["floors"]:
                # 生成位置编码
                building_code = "A" if "A" in building else "B"
                floor_num = self._extract_floor_number(floor)
                
                if floor_num:
                    location_code = f"LOC-{building_code}-{floor_num:02d}-"
                    location_queries.append(f"{location_code}相关的设备")
                    location_queries.append(f"位于{location_code}的设备")
        
        return location_queries
    
    def _extract_floor_number(self, floor_str: str) -> int:
        """从楼层字符串提取数字"""
        # 处理各种楼层表示
        if floor_str in ["一层", "1层", "1F"]:
            return 1
        elif floor_str in ["二层", "2层", "2F"]:
            return 2
        elif floor_str in ["三层", "3层", "3F"]:
            return 3
        elif floor_str in ["四层", "4层", "4F"]:
            return 4
        elif floor_str in ["五层", "5层", "5F"]:
            return 5
        else:
            # 尝试提取数字
            import re
            match = re.search(r"\d+", floor_str)
            return int(match.group()) if match else None

def test_query_enhancer():
    """测试查询增强器"""
    enhancer = QueryEnhancer()
    
    test_queries = [
        "A栋3F有哪些设备？",
        "A栋三层的空调设备",
        "B栋2层配电箱位置",
        "地下一层有什么设备"
    ]
    
    for query in test_queries:
        result = enhancer.enhance_query(query)
        print(f"\n原查询: {query}")
        print(f"查询类型: {result['query_type']}")
        print(f"提取实体: {result['extracted_entities']}")
        print(f"增强查询: {result['enhanced_queries']}")

if __name__ == "__main__":
    test_query_enhancer()
