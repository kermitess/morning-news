"""Define the pipeline graph using LangGraph."""

from __future__ import annotations

from langgraph.graph import StateGraph

from nodes import (
    assess,
    fetch,
    format_output,
    limit,
    rank,
    translate_summarize,
)
from state import PipelineState


def build_graph() -> StateGraph:
    """Build the pipeline graph.

    Flow: fetch → translate_summarize → assess → rank → limit → output
    """
    graph = StateGraph(PipelineState)

    # Add nodes
    graph.add_node("fetch", fetch)
    graph.add_node("translate_summarize", translate_summarize)
    graph.add_node("assess", assess)
    graph.add_node("rank", rank)
    graph.add_node("limit", limit)
    graph.add_node("output", format_output)

    # Wire in sequence
    graph.set_entry_point("fetch")
    graph.add_edge("fetch", "translate_summarize")
    graph.add_edge("translate_summarize", "assess")
    graph.add_edge("assess", "rank")
    graph.add_edge("rank", "limit")
    graph.add_edge("limit", "output")

    return graph


# Build and compile at module level
graph = build_graph().compile()
