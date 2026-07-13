import os
import tempfile
import textwrap
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from config import reload_config
from utils import call_llm_api


LLM_ENV_KEYS = [
    "LLM_MODEL",
    "LLM_BASE_URL",
    "LLM_API_KEY",
    "LLM_TEMPERATURE",
    "LLM_MAX_TOKENS",
    "OPENAI_PROVIDER",
    "API_VERSION",
]


class LLMConfigTest(unittest.TestCase):
    def setUp(self):
        self.env_patcher = patch.dict(os.environ, {}, clear=False)
        self.env_patcher.start()
        for key in LLM_ENV_KEYS:
            os.environ.pop(key, None)

    def tearDown(self):
        self.env_patcher.stop()

    def _write_config(self) -> str:
        config_text = """
        datasets:
          demo:
            corpus_path: data/demo/demo_corpus.json
            qa_path: data/demo/demo.json
            schema_path: schemas/demo.json
            graph_output: output/graphs/demo_new.json
        triggers:
          constructor_trigger: true
          retrieve_trigger: true
          mode: agent
        construction:
          mode: agent
          max_workers: 1
          chunk_size: 1000
          overlap: 100
        retrieval:
          top_k: 5
          faiss:
            search_k: 10
            max_workers: 1
            device: cpu
          agent:
            max_steps: 1
        embeddings:
          model_name: all-MiniLM-L6-v2
          device: cpu
          batch_size: 1
          max_length: 128
        nlp:
          spacy_model: en_core_web_lg
        llm:
          model: config-model
          base_url: https://config.example/v1
          api_key: config-key
          provider: openai
          temperature: 0.6
          max_tokens: 123
        output:
          base_dir: output
          graphs_dir: output/graphs
          chunks_dir: output/chunks
          logs_dir: output/logs
        performance:
          parallel_processing: true
          max_workers: 1
          batch_size: 1
          memory_optimization: true
        """
        config_file = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False)
        config_file.write(textwrap.dedent(config_text))
        config_file.close()
        self.addCleanup(lambda: os.path.exists(config_file.name) and os.unlink(config_file.name))
        return config_file.name

    def test_config_manager_loads_and_overrides_llm_config(self):
        config = reload_config(self._write_config())

        self.assertEqual(config.llm.model, "config-model")
        self.assertEqual(config.llm.base_url, "https://config.example/v1")
        self.assertEqual(config.llm.temperature, 0.6)
        self.assertEqual(config.llm.max_tokens, 123)

        config.override_config({"llm": {"temperature": 0.2, "max_tokens": 456}})

        self.assertEqual(config.llm.temperature, 0.2)
        self.assertEqual(config.llm.max_tokens, 456)
        self.assertEqual(config.to_dict()["llm"]["model"], "config-model")

    def test_llm_call_uses_config_defaults_and_env_overrides(self):
        reload_config(self._write_config())
        os.environ["LLM_API_KEY"] = "env-key"
        os.environ["LLM_TEMPERATURE"] = "0.9"
        os.environ["LLM_MAX_TOKENS"] = "321"

        fake_completion = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="OK"))]
        )
        fake_client = Mock()
        fake_client.chat.completions.create.return_value = fake_completion

        with patch.object(call_llm_api, "OpenAI", return_value=fake_client) as openai_cls:
            client = call_llm_api.LLMCompletionCall()
            response = client.call_api("hello")

        openai_cls.assert_called_once_with(
            base_url="https://config.example/v1",
            api_key="env-key",
        )
        fake_client.chat.completions.create.assert_called_once_with(
            model="config-model",
            messages=[{"role": "user", "content": "hello"}],
            temperature=0.9,
            max_tokens=321,
        )
        self.assertEqual(response, "OK")


if __name__ == "__main__":
    unittest.main()
