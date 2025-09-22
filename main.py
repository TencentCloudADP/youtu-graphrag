"""
- noagent: Basic retrieval and answer generation
- agent: Question decomposition with parallel sub-question processing and Iterative Retrieval Chain of Thought with step-by-step reasoning
"""
import json
import json_repair
import time
import argparse
import os
import glob
import shutil
from typing import List

from models.constructor import kt_gen as constructor
from models.retriever import agentic_decomposer as decomposer, enhanced_kt_retriever as retriever
from utils.eval import Eval
from config import get_config, ConfigManager
from utils.logger import logger


def tuples_to_string(rows, sep=", ", line_sep="\n", wrap_brackets=True):
    def fmt(t):
        inner = sep.join(map(str, t))
        return f"[{inner}]" if wrap_brackets else inner
    return line_sep.join(fmt(t) for t in rows)


def rerank_chunks_by_keywords(chunks: List[str], question: str, top_k: int) -> List[str]:
    """
    Rerank chunks by keyword matching with the question
    
    Args:
        chunks: List of chunk contents
        question: Original question
        top_k: Number of top chunks to return
        
    Returns:
        Reranked list of chunks
    """
    if len(chunks) <= top_k:
        return chunks
    
    question_keywords = set(question.lower().split())
    scored_chunks = []
    
    for chunk in chunks:
        chunk_lower = chunk.lower()
        score = sum(1 for keyword in question_keywords if keyword in chunk_lower)
        scored_chunks.append((chunk, score))
    
    scored_chunks.sort(key=lambda x: x[1], reverse=True)
    
    return [scored_chunk[0] for scored_chunk in scored_chunks[:top_k]]


def deduplicate_triples(triples: List[str]) -> List[str]:

    return list(set(triples))


def merge_chunk_contents(chunk_ids, chunk_contents_dict):

    return [chunk_contents_dict.get(chunk_id, f"[Missing content for chunk {chunk_id}]") for chunk_id in chunk_ids]


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Youtu-GraphRAG Framework")
    parser.add_argument(
        "--config", 
        type=str, 
        default="config/base_config.yaml",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--datasets", 
        nargs="+", 
        default=["demo"],
        help="List of datasets to process"
    )

    parser.add_argument(
        "--override",
        type=str,
        help="JSON string with configuration overrides"
    )
    return parser.parse_args()


def setup_environment(config: ConfigManager):
    """Set up the environment based on configuration."""
    config.create_output_directories()
    
    logger.info("Youtu-GraphRAG initialized")
    logger.info(f"Mode: {config.triggers.mode}")
    logger.info(f"Constructor enabled: {config.triggers.constructor_trigger}")
    logger.info(f"Retriever enabled: {config.triggers.retrieve_trigger}")


def clear_cache_files(dataset_name: str) -> None:
    """Clear cache files for a dataset before graph construction (CLI path)."""
    try:
        faiss_cache_dir = f"retriever/faiss_cache_new/{dataset_name}"
        if os.path.exists(faiss_cache_dir):
            shutil.rmtree(faiss_cache_dir)
            logger.info(f"Cleared FAISS cache directory: {faiss_cache_dir}")

        chunk_file = f"output/chunks/{dataset_name}.txt"
        if os.path.exists(chunk_file):
            os.remove(chunk_file)
            logger.info(f"Cleared chunk file: {chunk_file}")

        graph_file = f"output/graphs/{dataset_name}_new.json"
        if os.path.exists(graph_file):
            os.remove(graph_file)
            logger.info(f"Cleared graph file: {graph_file}")

        cache_patterns = [
            f"output/logs/{dataset_name}_*.log",
            f"output/chunks/{dataset_name}_*",
            f"output/graphs/{dataset_name}_*",
        ]
        for pattern in cache_patterns:
            for file_path in glob.glob(pattern):
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        logger.info(f"Cleared cache file: {file_path}")
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                        logger.info(f"Cleared cache directory: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to clear {file_path}: {e}")

        logger.info(f"Cache cleanup completed for dataset: {dataset_name}")

    except Exception as e:
        logger.error(f"Error clearing cache files for {dataset_name}: {e}")


def graph_construction(datasets):
    if config.triggers.constructor_trigger:
        logger.info("Starting knowledge graph construction...")
        
        for dataset in datasets:
            
            try:
                dataset_config = config.get_dataset_config(dataset)
                logger.info(f"Building knowledge graph for dataset: {dataset}")
                logger.info("Clearing caches before construction...")
                clear_cache_files(dataset)
                
                builder = constructor.KTBuilder(
                    dataset, 
                    dataset_config.schema_path, 
                    mode=config.construction.mode,
                    config=config
                )

                builder.build_knowledge_graph(dataset_config.corpus_path)
                logger.info(f"Successfully built knowledge graph for {dataset}")
            
            except Exception as e:
                logger.error(f"Failed to build knowledge graph for {dataset}: {e}")
                continue
    return


def retrieval(datasets):
    for dataset in datasets:
        dataset_config = config.get_dataset_config(dataset)
        
        with open(dataset_config.qa_path, "r") as f:
            qa_pairs = json_repair.load(f)
        
        # evaluator = Eval(config.api.llm_api_key)
        graphq = decomposer.GraphQ(dataset, config=config)
        
        logger.info("🚀 Initializing retriever 🚀")
        logger.info("-"*30)
        
        kt_retriever = retriever.KTRetriever(
            dataset, 
            dataset_config.graph_output, 
            recall_paths=config.retrieval.recall_paths,
            schema_path=dataset_config.schema_path, 
            top_k=config.retrieval.top_k_filter, 
            mode=config.triggers.mode,
            config=config
        )
        
        logger.info("🚀 Building FAISS index 🚀")
        logger.info("-"*30)
        start_time = time.time()
        kt_retriever.build_indices()
        logger.info(f"Time taken to build FAISS index: {time.time() - start_time} seconds")
        logger.info("-"*30)
        
        logger.info(f"Start answering questions...")
        logger.info("-"*30)
    
        if config.triggers.mode == "noagent":
            no_agent_retrieval(graphq, kt_retriever, qa_pairs, dataset_config.schema_path)

        elif config.triggers.mode == "agent":
            agent_retrieval(graphq, kt_retriever, qa_pairs, dataset_config.schema_path)


def initial_question_decomposition(graphq, kt_retriever, question, schema_path):
    """
    Process a single question using noagent mode and return structured results.
    
    Args:
        graphq: GraphQ decomposer instance
        kt_retriever: KTRetriever instance
        question: The question to process
        schema_path: Path to schema file
        
    Returns:
        dict: Contains decomposition_result, retrieval_results, and initial_answer
    """
    all_triples = set()
    all_chunk_ids = set()
    all_chunk_contents = dict()
    all_sub_question_results = []
    total_time = 0

    try:
        decomposition_result = graphq.decompose(question, schema_path)
        sub_questions = decomposition_result.get("sub_questions", [])
        involved_types = decomposition_result.get("involved_types", {})
        logger.info(f"Original question: {question}")
        logger.info(f"Decomposed into {len(sub_questions)} sub-questions")
        logger.info(f"Involved types: {involved_types}")
    except Exception as e:
        logger.error(f"Error decomposing question: {str(e)}")
        sub_questions = [{"sub-question": question}]
        involved_types = {"nodes": [], "relations": [], "attributes": []}  

    if len(sub_questions) > 1:
        logger.info("🚀 Using parallel sub-question processing...")
        aggregated_results, parallel_time = kt_retriever.process_subquestions_parallel(
            sub_questions, top_k=config.retrieval.top_k_filter, involved_types=involved_types
        )
        total_time += parallel_time
        all_triples.update(aggregated_results['triples'])
        all_chunk_ids.update(aggregated_results['chunk_ids'])
        for chunk_id, content in aggregated_results['chunk_contents'].items():
            all_chunk_contents[chunk_id] = content
        all_sub_question_results = aggregated_results['sub_question_results']
        logger.info(f"✅ Parallel processing completed in {parallel_time:.2f}s")

    else:
        logger.info("📝 Using single sub-question processing...")
        for i, sub_question in enumerate(sub_questions):
            try:
                sub_question_text = sub_question["sub-question"]
                logger.info(f"Processing sub-question {i+1}: {sub_question_text}")
                retrieval_results, time_taken = kt_retriever.process_retrieval_results(sub_question_text, top_k=config.retrieval.top_k_filter, involved_types=involved_types)
                total_time += time_taken
                triples = retrieval_results.get('triples', []) or []
                chunk_ids = retrieval_results.get('chunk_ids', []) or []
                chunk_contents = retrieval_results.get('chunk_contents', []) or []
                sub_result = {
                    'sub_question': sub_question_text,
                    'triples_count': len(triples),
                    'chunk_ids_count': len(chunk_ids),
                    'time_taken': time_taken
                }
                all_sub_question_results.append(sub_result)
                all_triples.update(triples)
                all_chunk_ids.update(chunk_ids)
                if isinstance(chunk_contents, dict):
                    for chunk_id, content in chunk_contents.items():
                        all_chunk_contents[chunk_id] = content
                else:
                    for i, chunk_id in enumerate(chunk_ids):
                        if i < len(chunk_contents):
                            all_chunk_contents[chunk_id] = chunk_contents[i]
                        else:
                            logger.debug(f"Missing chunk content for chunk_id {chunk_id}")

                logger.info(f"Sub-question {i+1} results: {len(retrieval_results['triples'])} triples, {len(retrieval_results['chunk_ids'])} chunks")

            except Exception as e:
                logger.error(f"Error processing sub-question {i+1}: {str(e)}")
                sub_result = {
                    'sub_question': sub_question_text,
                    'triples_count': 0,
                    'chunk_ids_count': 0,
                    'time_taken': 0.0
                }
                all_sub_question_results.append(sub_result)
                continue
            
    dedup_triples = deduplicate_triples(list(all_triples))
    dedup_chunk_ids = list(set(all_chunk_ids))
    dedup_chunk_contents = merge_chunk_contents(dedup_chunk_ids, all_chunk_contents)

    if not dedup_triples and not dedup_chunk_contents:
        logger.warning(f"No triples or chunks retrieved for question: {question}")
        dedup_triples = ["No relevant information found"]
        dedup_chunk_contents = ["No relevant chunks found"]

    if len(dedup_triples) > 20: 
        question_keywords = set(question.lower().split())
        scored_triples = []
        for triple in dedup_triples:
            triple_lower = triple.lower()
            score = sum(1 for keyword in question_keywords if keyword in triple_lower)
            scored_triples.append((triple, score))

        scored_triples.sort(key=lambda x: x[1], reverse=True)
        dedup_triples = [triple for triple, score in scored_triples[:config.retrieval.top_k_filter]]

    if len(dedup_chunk_contents) > config.retrieval.top_k_filter:
        dedup_chunk_contents = rerank_chunks_by_keywords(dedup_chunk_contents, question, config.retrieval.top_k_filter)

    context = "=== Triples ===\n" + "\n".join(dedup_triples)
    context += "\n=== Chunks ===\n" + "\n".join(dedup_chunk_contents)

    for i, sub_result in enumerate(all_sub_question_results):
        logger.info(f"  Sub-{i+1}: {sub_result['sub_question']} -> {sub_result['triples_count']} triples, {sub_result['chunk_ids_count']} chunks ({sub_result['time_taken']:.2f}s)")

    prompt = kt_retriever.generate_prompt(question, context)

    max_retries = 20
    initial_answer = None
    for retry in range(max_retries):
        try:
            initial_answer = kt_retriever.generate_answer(prompt)
            if initial_answer and initial_answer.strip():
                break
        except Exception as e:
            logger.error(f"Error generating answer (attempt {retry + 1}): {str(e)}")
            if retry == max_retries - 1:
                initial_answer = "Error: Unable to generate answer"
            time.sleep(1)

    return {
        'decomposition_result': decomposition_result,
        'sub_questions': sub_questions,
        'involved_types': involved_types,
        'triples': dedup_triples,
        'chunk_ids': dedup_chunk_ids,
        'chunk_contents': dedup_chunk_contents,
        'sub_question_results': all_sub_question_results,
        'initial_answer': initial_answer,
        'total_time': total_time
    }


def no_agent_retrieval(graphq, kt_retriever, qa_pairs, schema_path):
    total_time = 0
    accuracy = 0
    total_questions = len(qa_pairs)
    evaluator = Eval()
    for qa in qa_pairs:
        result = initial_question_decomposition(graphq, kt_retriever, qa["question"], schema_path)
        total_time += result['total_time']

        logger.info(f"========== Original Question: {qa['question']} ==========") 
        logger.info(f"Gold Answer: {qa['answer']}")
        logger.info(f"Generated Answer: {result['initial_answer']}")
        logger.info("-"*30)


        eval_result = evaluator.eval(qa["question"], qa["answer"], result['initial_answer'])
        logger.info(f"No agent mode eval result: {eval_result}")
        if eval_result == "1":
            accuracy += 1
    logger.info(f"Eval result: {'Correct' if eval_result == '1' else 'Wrong'}")
    logger.info(f"Overall Accuracy: {accuracy/total_questions*100}%")     
    logger.info(f"Average time taken: {total_time/total_questions} seconds")


def agent_retrieval(graphq, kt_retriever, qa_pairs, schema_path):
    total_time = 0
    accuracy = 0
    total_questions = len(qa_pairs)
    evaluator = Eval()
    max_steps = config.retrieval.agent.max_steps 
                    
    for qa in qa_pairs:
        step = 1
        current_query = qa["question"]
        thoughts = []
        all_triples = set()
        all_chunk_ids = set()
        all_chunk_contents = dict()
        logs = []
        
        logger.info(f"🚀 Starting Agent mode for question: {current_query}")
        
        # First, run noagent mode to get initial results and answer
        logger.info("📝 Step 0: Running noagent mode for initial analysis...")
        initial_result = initial_question_decomposition(graphq, kt_retriever, current_query, schema_path)
        total_time += initial_result['total_time']
        
        # Use noagent results as initial knowledge base
        all_triples.update(initial_result['triples'])
        all_chunk_ids.update(initial_result['chunk_ids'])
        for chunk_id, content in zip(initial_result['chunk_ids'], initial_result['chunk_contents']):
            all_chunk_contents[chunk_id] = content
        
        # Use noagent answer as initial thought
        initial_thought = f"Initial analysis (noagent mode): {initial_result['initial_answer']}"
        thoughts.append(initial_thought)
        
        logger.info(f"✅ Noagent analysis completed. Initial answer: {initial_result['initial_answer'][:100]}...")
        logger.info(f"📊 Retrieved {len(initial_result['triples'])} triples and {len(initial_result['chunk_ids'])} chunks from noagent")
        
        logger.info(f"🚀 Starting IRCoT for question: {current_query}")
    
        while step <= max_steps:
            logger.info(f"📝 IRCoT Step {step}/{max_steps}")
            
            dedup_triples = deduplicate_triples(list(all_triples))
            dedup_chunk_ids = list(set(all_chunk_ids))
            dedup_chunk_contents = merge_chunk_contents(dedup_chunk_ids, all_chunk_contents)
            
            context = "=== Triples ===\n" + "\n".join(dedup_triples)
            context += "\n=== Chunks ===\n" + "\n".join(dedup_chunk_contents)
            
            ircot_prompt = f"""
                            You are an expert knowledge assistant using iterative retrieval with chain-of-thought reasoning.
                            
                            Current Question: {current_query}
                            
                            Available Knowledge Context:
                            {context}
                            
                            Previous Thoughts: {' | '.join(thoughts) if thoughts else 'None'}
                            
                            Step {step}: Please think step by step about what additional information you need to answer the question completely and accurately.
                            
                            Instructions:
                            1. Analyze the current knowledge context and the question
                            2. Consider the initial analysis from noagent mode (if available in previous thoughts)
                            3. Think about what information might be missing or unclear
                            4. If you have enough information to answer, in the end of your response, write "So the answer is:" followed by your final answer
                            5. If you need more information, in the end of your response, write a specific query begin with "The new query is:" to retrieve additional relevant information
                            6. Be specific and focused in your reasoning
                            7. Build upon the initial analysis to provide deeper insights
                            
                            Your reasoning:
                            """
            max_retries = 20
            response = None
            for retry in range(max_retries):
                try:
                    response = kt_retriever.generate_answer(ircot_prompt)
                    if response and response.strip():
                        break
                except Exception as e:
                    logger.error(f"Error generating IRCoT response (attempt {retry + 1}): {str(e)}")
                    if retry == max_retries - 1:
                        response = "Error: Unable to generate reasoning"
                    time.sleep(1)
            
            thoughts.append(response)
            
            logs.append({
                "step": step,
                "query": current_query,
                "retrieved_triples_count": len(dedup_triples),
                "retrieved_chunks_count": len(dedup_chunk_contents),
                "response": response,
                "thoughts": thoughts.copy()
            })
            
            logger.info(f"Step {step} response: {response[:100]}...")
            
            if "So the answer is:" in response:
                logger.info("✅ Final answer found, stopping IRCoT")
                break

            if "The new query is:" in response:
                new_query = response.split("The new query is:")[1].strip()
            else:
                new_query = response
            
            if new_query and new_query != current_query:
                current_query = new_query
                logger.info(f"🔄 New query for next iteration: {current_query}")
                
                retrieval_results, time_taken = kt_retriever.process_retrieval_results(current_query, top_k=config.retrieval.top_k_filter)
                total_time += time_taken
                
                new_triples = retrieval_results.get('triples', []) or []
                new_chunk_ids = retrieval_results.get('chunk_ids', []) or []
                new_chunk_contents = retrieval_results.get('chunk_contents', []) or []
                
                if isinstance(new_chunk_contents, list):
                    new_chunk_contents_dict = {}
                    for i, chunk_id in enumerate(new_chunk_ids):
                        if i < len(new_chunk_contents):
                            new_chunk_contents_dict[chunk_id] = new_chunk_contents[i]
                        else:
                            new_chunk_contents_dict[chunk_id] = f"[Missing content for chunk {chunk_id}]"
                else:
                    new_chunk_contents_dict = new_chunk_contents
                
                all_triples.update(new_triples)
                all_chunk_ids.update(new_chunk_ids)
                all_chunk_contents.update(new_chunk_contents_dict)
                
                logger.info(f"Retrieved {len(new_triples)} new triples, {len(new_chunk_ids)} new chunks")
            else:
                logger.info("No new query generated, stopping IRCoT")
                break
            
            step += 1
        
        final_context = "=== Final Triples ===\n" + "\n".join(deduplicate_triples(list(all_triples)))
        final_context += "\n=== Final Chunks ===\n" + "\n".join(merge_chunk_contents(list(set(all_chunk_ids)), all_chunk_contents))
        
        final_prompt = kt_retriever.generate_prompt(qa["question"], final_context)
        
        max_retries = 20
        answer = None
        for retry in range(max_retries):
            try:
                answer = kt_retriever.generate_answer(final_prompt)
                if answer and answer.strip():
                    break
            except Exception as e:
                logger.error(f"Error generating final answer (attempt {retry + 1}): {str(e)}")
                if retry == max_retries - 1:
                    answer = "Error: Unable to generate answer"
                time.sleep(1)
        
        logger.info(f"========== Original Question: {qa['question']} ==========") 
        logger.info(f"Noagent Initial Answer: {initial_result['initial_answer']}")
        logger.info(f"IRCoT Steps: {len(thoughts)}")
        logger.info(f"Final Triples: {len(deduplicate_triples(list(all_triples)))}")
        logger.info(f"Final Chunks: {len(merge_chunk_contents(list(set(all_chunk_ids)), all_chunk_contents))}")
        logger.info(f"Gold Answer: {qa['answer']}")
        logger.info(f"Generated Answer: {answer}")
        logger.info(f"Thought Process: {' | '.join(thoughts)}")
        logger.info("-"*30)
        
        eval_result = evaluator.eval(qa["question"], qa["answer"], answer)
        logger.info(f"Agent mode eval result: {eval_result}")
        if eval_result == "1":
            accuracy += 1
    logger.info(f"Eval result: {'Correct' if eval_result == '1' else 'Wrong'}")
    logger.info(f"Overall Accuracy: {accuracy/total_questions*100}%")
    logger.info(f"Average time taken: {total_time/total_questions} seconds")


if __name__ == "__main__":
    args = parse_arguments()
    config_path = args.config
    config = get_config(config_path)
    
    if args.override:
        try:
            overrides = json.loads(args.override)
            config.override_config(overrides)
            logger.info("Applied configuration overrides")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in override parameter: {e}")
            exit(1)
    
    setup_environment(config)
    
    datasets = args.datasets
    
    # ########### Construction ###########
    if config.triggers.constructor_trigger:
        logger.info("Starting knowledge graph construction...")
        graph_construction(datasets)

    # ########### Retriever ###########
    if config.triggers.retrieve_trigger:
        logger.info("Starting knowledge retrieval and QA...")
        retrieval(datasets)