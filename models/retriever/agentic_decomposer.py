import json_repair
from  utils import call_llm_api

try:
    from config import get_config
except ImportError:
    get_config = None

class GraphQ:
    def __init__(self, dataset_name, config=None):
        if config is None and get_config is not None:
            try:
                self.config = get_config()
            except Exception:
                self.config = None
        else:
            self.config = config
        self.llm_client = call_llm_api.LLMCompletionCall()
        self.dataset_name = dataset_name
            
    def read_schema(self, schema_path: str) -> str:
        with open(schema_path, "r") as f:
            schema = f.read()
        return schema
    
    def prompt_format(self, schema: str, question: str) -> str:
        if self.config:
            if self.dataset_name == "anony_chs":
                return self.config.get_prompt_formatted("decomposition", "anony_chs", ontology=schema, question=question)
            else:
                return self.config.get_prompt_formatted("decomposition", "general", ontology=schema, question=question)
        else:
            if self.dataset_name == "anony_chs":
                return f"""
                你是一个专业的问题分解大师，请根据以下问题和图本体模式，将问题分解为2-3个子问题。
                要求：
                1. 每个子问题必须：
                   - 明确且专注于一个事实或关系，通过识别所有实体、关系和推理步骤
                   - 明确引用原始问题中的实体和关系
                   - 设计为检索最终答案所需的相关知识
                2. 对于简单问题（1-2跳），返回原始问题作为单个子问题
                3. 返回一个JSON数组，每个子问题是一个字符串。
                
                问题：{question}
                
                图本体模式：{schema}
                
                请返回一个JSON数组，每个子问题是一个字符串。
                示例：
                原始问题："智取生辰纲事件中，PERSON#1的策略为什么能够成功"
                子问题：
                [
                    {{"sub-question": "智取生辰纲中PERSON#1的策略是什么？"}},
                    {{"sub-question": "智取生辰纲中的PERSON、LOCATION有什么特殊属性？"}},
                ]
                如果是简单问题，返回原始问题作为单个子问题。
                原始问题："智取生辰纲事件中，PERSON#1是谁"
                子问题：
                [
                    {{"sub-question": "智取生辰纲事件中，PERSON#1是谁？"}}
                ]
                """
            else:
                return f"""
                You are a professional question decomposition expert specializing in multi-hop reasoning.
                Given the following schema and the question, decompose the complex question into 2-3 focused sub-questions.

                CRITICAL REQUIREMENTS:
                1. Each sub-question must be:
                   - Specific and focused on a single fact or relationship by identifing all entities, relationships, and reasoning steps needed
                   - Answerable independently with the given schema
                   - Explicitly reference entities and relations from the original question
                   - Designed to retrieve relevant knowledge for the final answer

                2. For simple questions (1-2 hop), return the original question as a single sub-question
                3. Return a JSON array, each sub-question is a string.

                Graph Schema:
                {schema}

                Question: {question}

                Example for complex question:
                Original: "Which film has the director died earlier, Ethnic Notions or Gordon Of Ghost City?"
                Sub-questions:
                [
                    {{"sub-question": "Who is the director of Ethnic Notions?"}},
                    {{"sub-question": "Who is the director of Gordon Of Ghost City?"}},
                    {{"sub-question": "When did the director of Ethnic Notions die?"}},
                    {{"sub-question": "When did the director of Gordon Of Ghost City die?"}}
                ]

                Example for simple question:
                Original: "What is the capital of France?"
                Sub-questions:
                [
                    {{"sub-question": "What is the capital of France?"}}
                ]
                """
    
    def decompose(self, question: str, schema_path: str) -> dict:
        schema = self.read_schema(schema_path)
        prompt = self.prompt_format(schema, question)
        response = self.llm_client.call_api(prompt)
        content = json_repair.loads(response)
        
        # Ensure backward compatibility - if old format, convert to new format
        if isinstance(content, list):
            content = {
                "sub_questions": content,
                "involved_types": {
                    "nodes": [],
                    "relations": [],
                    "attributes": []
                }
            }
        
        return content  
