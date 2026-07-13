import unittest

import networkx as nx

from models.retriever.enhanced_kt_retriever import KTRetriever


class SchemaTypeFilteringTest(unittest.TestCase):
    def setUp(self):
        self.retriever = KTRetriever.__new__(KTRetriever)
        self.retriever.graph = nx.Graph()
        self.retriever.graph.add_node(
            "person_1",
            label="entity",
            properties={"schema_type": "person"},
        )
        self.retriever.graph.add_node(
            "movie_1",
            label="entity",
            properties={"schema_type": "creative_work"},
        )
        self.retriever.graph.add_node(
            "legacy_entity",
            label="entity",
            properties={},
        )

    def test_empty_target_types_keep_full_graph_fallback(self):
        self.assertCountEqual(
            self.retriever._filter_nodes_by_schema_type([]),
            ["person_1", "movie_1", "legacy_entity"],
        )

    def test_target_types_exclude_untyped_entities(self):
        self.assertEqual(
            self.retriever._filter_nodes_by_schema_type(["person"]),
            ["person_1"],
        )


if __name__ == "__main__":
    unittest.main()
