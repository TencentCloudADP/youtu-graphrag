import unittest

import networkx as nx

from models.retriever.enhanced_kt_retriever import KTRetriever


class OneHopTriplesTest(unittest.TestCase):
    """_get_one_hop_triples_from_nodes must emit graph node IDs.

    Every consumer of ``path1_results['one_hop_triples']`` looks the head/tail
    up in ``self.graph`` (``_get_node_text``, ``_get_node_properties``,
    ``_extract_chunk_ids_from_triples``), so emitting the ``name`` property
    instead of the node ID silently loses node text, properties and chunk
    provenance.  Node IDs follow the scheme produced by
    ``utils.graph_processor.load_graph_from_json`` (``<label>_<counter>``).
    """

    def setUp(self):
        self.retriever = KTRetriever.__new__(KTRetriever)
        self.retriever.top_k = 10
        self.retriever.graph = nx.MultiDiGraph()
        self.retriever.graph.add_node(
            "entity_0",
            label="entity",
            level=2,
            properties={"name": "FC Barcelona", "chunk id": "c0",
                        "schema_type": "organization"},
        )
        self.retriever.graph.add_node(
            "entity_1",
            label="entity",
            level=2,
            properties={"name": "Copa del Rey", "chunk id": "c0",
                        "schema_type": "event"},
        )
        self.retriever.graph.add_edge("entity_0", "entity_1",
                                      relation="participates_in")

    def test_triples_use_node_ids(self):
        self.assertEqual(
            self.retriever._get_one_hop_triples_from_nodes(["entity_0"]),
            [("entity_0", "participates_in", "entity_1")],
        )

    def test_triple_endpoints_resolve_for_consumers(self):
        head, relation, tail = self.retriever._get_one_hop_triples_from_nodes(
            ["entity_0"]
        )[0]
        self.assertEqual(self.retriever._get_node_text(head), "FC Barcelona")
        self.assertEqual(self.retriever._get_node_properties(head),
                         "[schema_type: organization]")
        self.assertEqual(
            self.retriever._extract_chunk_ids_from_triples(
                [(head, relation, tail, 1.0)]
            ),
            {"c0"},
        )


if __name__ == "__main__":
    unittest.main()
