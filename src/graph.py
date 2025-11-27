from typing import TypedDict, Annotated, Sequence, List, Union, Optional
from langchain_core.messages import BaseMessage
import operator
from langgraph.graph import StateGraph, END
from src.agents import Agents

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    data_path: str
    schema_info: dict
    generated_code: str
    thinking_process: str
    execution_result: dict
    validation_error: Union[str, None]
    final_answer: str
    # New agent outputs
    query_type: Optional[str]
    suggested_insights: Optional[str]
    anomalies: Optional[List[str]]
    optimization_suggestions: Optional[List[str]]
    code_explanation: Optional[str]
    execution_plan: Optional[str]
    plot_path: Optional[str]

def create_graph():
    agents = Agents()
    
    workflow = StateGraph(AgentState)
    
    # Add all nodes (4 core + 7 new = 11 agents)
    # Core workflow
    workflow.add_node("query_classifier", agents.query_classifier)
    workflow.add_node("query_generator", agents.query_generator)
    workflow.add_node("query_optimizer", agents.query_optimizer)
    workflow.add_node("code_executor", agents.code_executor)
    workflow.add_node("validator", agents.validator)
    workflow.add_node("summarizer", agents.summarizer)
    # Additional agents
    workflow.add_node("insight_generator", agents.insight_generator)
    workflow.add_node("explanation", agents.explanation_agent)
    
    # Define flow: classifier -> generator -> optimizer -> executor -> validator -> summarizer -> insight + explanation
    workflow.set_entry_point("query_classifier")
    
    workflow.add_edge("query_classifier", "query_generator")
    workflow.add_edge("query_generator", "query_optimizer")
    workflow.add_edge("query_optimizer", "code_executor")
    workflow.add_edge("code_executor", "validator")
    
    def validation_router(state):
        if state.get("validation_error"):
            return "summarizer" 
        return "summarizer"

    workflow.add_conditional_edges(
        "validator",
        validation_router,
        {
            "summarizer": "summarizer"
        }
    )
    
    # After summarizer, run insight generator and explanation in parallel
    workflow.add_edge("summarizer", "insight_generator")
    workflow.add_edge("insight_generator", "explanation")
    workflow.add_edge("explanation", END)
    
    return workflow.compile()
