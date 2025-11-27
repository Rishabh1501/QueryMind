"""
Agent workflow visualization component for Streamlit.
"""
import streamlit as st
from typing import Dict, Any, List

class AgentWorkflowTracker:
    """Visual tracker for agent execution workflow."""
    
    AGENT_WORKFLOW = [
        {"name": "Query Classifier", "key": "query_classifier", "icon": "🎯", "description": "Categorizing query type"},
        {"name": "Query Generator", "key": "query_generator", "icon": "💭", "description": "Generating Python code"},
        {"name": "Query Optimizer", "key": "query_optimizer", "icon": "⚡", "description": "Optimizing code quality"},
        {"name": "Code Executor", "key": "code_executor", "icon": "🐳", "description": "Running in Docker"},
        {"name": "Validator", "key": "validator", "icon": "✅", "description": "Validating results"},
        {"name": "Summarizer", "key": "summarizer", "icon": "📝", "description": "Creating answer"},
        {"name": "Insight Generator", "key": "insight_generator", "icon": "💡", "description": "Generating insights"},
        {"name": "Explanation", "key": "explanation", "icon": "📚", "description": "Explaining code"},
    ]
    
    @staticmethod
    def render_workflow(current_step: str = None, result: Dict[str, Any] = None):
        """
        Render the agent workflow visualization.
        
        Args:
            current_step: Currently executing agent (during processing)
            result: Complete result dict (after processing)
        """
        st.markdown("### 🔄 Agent Workflow")
        
        # Create columns for agent cards
        cols = st.columns(4)
        
        for idx, agent in enumerate(AgentWorkflowTracker.AGENT_WORKFLOW):
            col = cols[idx % 4]
            
            with col:
                # Determine agent status
                is_complete = result is not None
                is_current = agent["key"] == current_step
                
                # Status indicator
                if is_complete:
                    status_icon = "✅"
                    status_color = "green"
                elif is_current:
                    status_icon = "⏳"
                    status_color = "blue"
                else:
                    status_icon = "⭕"
                    status_color = "gray"
                
                # Agent card
                with st.container():
                    st.markdown(f"""
                    <div style="border: 2px solid {status_color}; border-radius: 10px; padding: 10px; margin-bottom: 10px; background-color: {'#0e1117' if not is_complete else '#1a1f2e'};">
                        <h4 style="margin: 0; color: {status_color};">{status_icon} {agent['icon']} {agent['name']}</h4>
                        <p style="margin: 5px 0 0 0; font-size: 0.8em; color: #888;">{agent['description']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # If complete, show output in expander
                    if is_complete and result:
                        AgentWorkflowTracker._render_agent_output(agent, result)
    
    @staticmethod
    def _render_agent_output(agent: Dict, result: Dict[str, Any]):
        """Render clickable output for a specific agent."""
        with st.expander(f"View {agent['name']} Output", expanded=False):
            key = agent["key"]
            
            # Query Classifier
            if key == "query_classifier":
                query_type = result.get("query_type", "N/A")
                st.write(f"**Query Type**: `{query_type}`")
            
            # Query Generator
            elif key == "query_generator":
                thinking = result.get("thinking_process", "")
                code = result.get("generated_code", "")
                if thinking:
                    st.markdown("**Thinking Process:**")
                    st.info(thinking[:200] + "..." if len(thinking) > 200 else thinking)
                if code:
                    st.code(code[:300] + "..." if len(code) > 300 else code, language="python")
            
            # Query Optimizer
            elif key == "query_optimizer":
                suggestions = result.get("optimization_suggestions", [])
                if suggestions:
                    for suggestion in suggestions:
                        st.warning(suggestion)
                else:
                    st.success("No optimizations needed")
            
            # Code Executor
            elif key == "code_executor":
                exec_result = result.get("execution_result", {})
                if exec_result.get("success"):
                    st.success("✅ Execution successful")
                    output = exec_result.get("output", "")
                    if output:
                        st.text(output[:200] + "..." if len(output) > 200 else output)
                else:
                    st.error(f"❌ Execution failed: {exec_result.get('error', 'Unknown')}")
            
            # Validator
            elif key == "validator":
                error = result.get("validation_error")
                if error:
                    st.error(f"Validation Error: {error}")
                else:
                    st.success("✅ Validation passed")
            
            # Summarizer
            elif key == "summarizer":
                answer = result.get("final_answer", "")
                st.markdown(answer[:300] + "..." if len(answer) > 300 else answer)
            
            # Insight Generator
            elif key == "insight_generator":
                insights = result.get("suggested_insights", "")
                if insights:
                    st.markdown(insights)
                else:
                    st.info("No insights generated")
            
            # Explanation
            elif key == "explanation":
                explanation = result.get("code_explanation", "")
                if explanation:
                    st.markdown(explanation)
                else:
                    st.info("No explanation generated")
    
    @staticmethod
    def render_compact_timeline(result: Dict[str, Any], agent_timings: Dict[str, float]):
        """Render a compact timeline view of agent execution."""
        st.markdown("#### ⏱️ Execution Timeline")
        
        total_time = sum(agent_timings.values())
        
        for agent in AgentWorkflowTracker.AGENT_WORKFLOW:
            key = agent["key"]
            duration = agent_timings.get(key, 0)
            
            if duration > 0:
                percentage = (duration / total_time * 100) if total_time > 0 else 0
                st.markdown(f"""
                <div style="margin: 5px 0;">
                    <span style="color: #888;">{agent['icon']} {agent['name']}</span>
                    <span style="float: right; color: #0ea5e9;">{duration:.2f}s ({percentage:.1f}%)</span>
                    <div style="background: #1a1f2e; height: 4px; border-radius: 2px; margin-top: 3px;">
                        <div style="background: #0ea5e9; width: {percentage}%; height: 4px; border-radius: 2px;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown(f"**Total Time**: {total_time:.2f}s")
