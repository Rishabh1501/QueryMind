import streamlit as st
import os
import tempfile
from src.graph import create_graph
from src.data_engine import DataEngine
from src.utils import load_config
from langchain_core.messages import HumanMessage, AIMessage
from src.workflow_viz import AgentWorkflowTracker
from src.cache_manager import ensure_redis_running
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="QueryMind", layout="wide")

# Ensure Redis is running
try:
    ensure_redis_running()
except Exception as e:
    st.error(f"⚠️ Redis cache unavailable: {e}. Caching will be disabled.")
    logger.warning(f"Redis not available: {e}")

st.title("QueryMind")

# Sidebar for configuration and file upload
with st.sidebar:
    st.header("Configuration")
    
    # File Upload
    uploaded_file = st.file_uploader("Upload Sales Data (CSV/Excel)", type=["csv", "xlsx", "xls"])
    
    if uploaded_file:
        # Save uploaded file to a temp location
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
        
        st.session_state['data_path'] = tmp_path
        st.success(f"File uploaded: {uploaded_file.name}")
        
        # Initialize Data Engine and get schema
        config = load_config()
        data_engine = DataEngine(config)
        try:
            schema_info = data_engine.load_data(tmp_path)
            st.session_state['schema_info'] = schema_info
            st.subheader("Data Preview")
            st.dataframe(schema_info['preview'], width='stretch')
        except Exception as e:
            st.error(f"Error loading data: {e}")
    
    # Chat Management
    st.divider()
    st.subheader("Chat Management")
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

# Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display Chat Messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat Input
if prompt := st.chat_input("Ask a question about your data..."):
    if 'data_path' not in st.session_state:
        st.error("Please upload a data file first.")
    else:
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Run LangGraph Workflow with real-time status
        with st.status("🤖 Processing query...", expanded=True) as status:
            try:
                status.update(label="💭 Query Generator", state="running")
                status.write("Analyzing query and generating Python code...")
                
                graph = create_graph()
                
                initial_state = {
                    "messages": [HumanMessage(content=prompt)],
                    "data_path": st.session_state['data_path'],
                    "schema_info": st.session_state['schema_info'],
                    "generated_code": "",
                    "thinking_process": "",
                    "execution_result": {},
                    "validation_error": None,
                    "final_answer": "",
                    # New agent fields
                    "query_type": None,
                    "suggested_insights": None,
                    "anomalies": None,
                    "optimization_suggestions": None,
                    "code_explanation": None,
                    "execution_plan": None,
                    "plot_path": None
                }
                
                # Invoke the graph
                result = graph.invoke(initial_state)
                
                status.update(label="✅ Complete", state="complete")
                
                final_answer = result.get("final_answer", "I couldn't generate an answer.")
                
                # Add assistant message to history
                st.session_state.messages.append({"role": "assistant", "content": final_answer})
                
                # Store result for workflow visualization
                st.session_state['last_result'] = result
                
            except Exception as e:
                status.update(label="❌ Error", state="error")
                st.error(f"An error occurred: {e}")
                final_answer = f"Error: {e}"
                result = {}
        
        # Display Agent Workflow Visualization
        if 'last_result' in st.session_state and st.session_state['last_result']:
            with st.container():
                AgentWorkflowTracker.render_workflow(result=st.session_state['last_result'])
                
                # Get agent timings from the graph's agents instance
                try:
                    agents_instance = graph.get_state(initial_state)
                    if hasattr(agents_instance, 'agent_timings'):
                        AgentWorkflowTracker.render_compact_timeline(
                            st.session_state['last_result'],
                            agents_instance.agent_timings
                        )
                except:
                    pass  # Skip timeline if timings not available
        
        # Display final answer (outside status block)
        with st.chat_message("assistant"):
            st.markdown(final_answer)
            
            # INLINE GRAPH DISPLAY (if available)
            plot_path = result.get("execution_result", {}).get("plot_path")
            if plot_path and os.path.exists(plot_path):
                st.image(plot_path, width='stretch', caption="Generated Visualization")
            
            # Suggested Insights (if available)
            suggested_insights = result.get("suggested_insights")
            if suggested_insights:
                with st.expander("💡 Suggested Follow-up Questions", expanded=False):
                    st.markdown(suggested_insights)
            
            # Optional: Show intermediate steps (code, etc.) in an expander
            with st.expander("View Analysis Details"):
                # Thinking Process
                thinking = result.get("thinking_process", "")
                if thinking:
                    st.subheader("💭 Thinking Process")
                    st.markdown(thinking)
                    st.divider()
                
                # Code Explanation (if available)
                code_explanation = result.get("code_explanation")
                if code_explanation:
                    st.subheader("📚 Code Explanation")
                    st.markdown(code_explanation)
                    st.divider()
                
                # Generated Code
                st.subheader("Generated Code")
                st.code(result.get("generated_code", ""), language="python")
                
                # Execution Output
                st.subheader("Execution Output")
                st.text(result.get("execution_result", {}).get("output", ""))
                
                # Optimization Suggestions (if any)
                opt_suggestions = result.get("optimization_suggestions")
                if opt_suggestions:
                    st.subheader("⚡ Optimization Suggestions")
                    for suggestion in opt_suggestions:
                        st.info(suggestion)
