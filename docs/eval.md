# Evaluation Framework

The `utu/eval/` module provides a standardized and extensible framework for benchmarking agents. It is designed to be modular, allowing for the easy addition of new datasets and evaluation methods. The entire workflow is orchestrated by `BaseBenchmark`, which ties together data management, benchmark-specific logic, and the agent being tested.

Here are the three core components of the framework:

## 1. Data Management (`DBDataManager`)

The `DBDataManager` is the persistence layer of the evaluation framework. It is responsible for loading datasets and tracking the state of every sample throughout the evaluation process.

- **Database Backend**: It uses a database (defaulting to SQLite) to store all evaluation data. Each sample is stored as an `EvaluationSample` record.
- **Experiment Tracking**: All samples are associated with an `exp_id` (Experiment ID). This allows for easy tracking and resuming of experiments. If you run an evaluation with an existing `exp_id`, the system will pick up where it left off.
- **Stateful Tracking**: Each `EvaluationSample` has a `stage` field (`init`, `rollout`, `judged`) that tracks its progress through the pipeline. This ensures that each step of the evaluation only processes the relevant samples.

## 2. Dataset Standardization (`Processer`)

A `Processer` handles all the logic that is specific to a particular benchmark (e.g., GAIA, BrowseComp). This design cleanly separates the generic evaluation flow from the details of each dataset.

- **`BaseProcesser` Interface**: This abstract class defines the contract for all processers, which must implement:
    - `preprocess_one()`: Prepares a raw data sample for the agent. This can involve reformatting the question, adding specific instructions, or attaching file paths.
    - `judge_one()`: Evaluates an agent's response for a single sample.
    - `calculate_metrics()`: Computes the final summary statistics for a benchmark.
- **Judging Strategies**: The framework provides different base implementations for judging:
    - `BaseLLMJudgeProcesser`: Uses a powerful LLM as a judge, guided by specialized prompt templates. This is suitable for complex, open-ended questions.
    - `BaseMatchProcesser`: Uses rule-based methods (e.g., exact string or number matching) for judging. This is faster and more suitable for questions with a single, precise answer.
- **`PROCESSER_FACTORY`**: A factory that automatically discovers and registers all available processers. The `BaseBenchmark` uses this factory to dynamically select the correct processer for each sample based on its `source` field.

## 3. Standardized Test Flow (`BaseBenchmark`)

`BaseBenchmark` is the main orchestrator that drives the entire evaluation pipeline from start to finish. It provides a standardized, four-stage process.

- **`preprocess`**: Loads all initial samples from the `DBDataManager` and uses the appropriate `Processer` to prepare them for the agent.
- **`rollout`**: Runs the configured agent on all the preprocessed samples. The agent's response, trajectory, and other metadata are saved back to the database for each sample.
- **`judge`**: Fetches the completed samples from the `rollout` stage and uses the `Processer` to evaluate whether the agent's response was correct.
- **`stat`**: Gathers all judged samples, groups them by benchmark, and uses the `Processer` to calculate and log the final metrics (e.g., accuracy).

This structured pipeline ensures that every evaluation is consistent, automated, and resilient, as it can be stopped and resumed at any stage.
