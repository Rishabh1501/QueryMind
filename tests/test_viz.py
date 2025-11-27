import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.graph import create_graph
from src.data_engine import DataEngine
from src.utils import load_config
from langchain_core.messages import HumanMessage

def test_visualization():
    print("Testing visualization capabilities...")
    
    # Load Config
    config = load_config()
    print("Config loaded.")
    
    # Initialize Data Engine
    data_engine = DataEngine(config)
    data_path = os.path.abspath("data/Sale Report.csv")
    
    if not os.path.exists(data_path):
        print(f"Error: Data file not found at {data_path}")
        return
        
    print(f"Loading data from {data_path}...")
    schema_info = data_engine.load_data(data_path)
    print("Data loaded.")
    
    # Create Graph
    graph = create_graph()
    print("Graph created.")
    
    # Define Query with visualization request
    query = "Show me a bar chart of stock by category"
    print(f"Query: {query}")
    
    # Initial State
    initial_state = {
        "messages": [HumanMessage(content=query)],
        "data_path": data_path,
        "schema_info": schema_info,
        "generated_code": "",
        "thinking_process": "",
        "execution_result": {},
        "validation_error": None,
        "final_answer": ""
    }
    
    # Invoke Graph
    print("Invoking graph...")
    try:
        result = graph.invoke(initial_state)
        print("Graph execution completed.")
        
        print("\n=== THINKING PROCESS ===")
        print(result.get('thinking_process', 'No thinking captured'))
        
        print("\n=== GENERATED CODE ===")
        print(result.get('generated_code'))
        
        print("\n=== EXECUTION OUTPUT ===")
        print(result.get('execution_result', {}).get('output'))
        
        print("\n=== PLOT PATH ===")
        plot_path = result.get('execution_result', {}).get('plot_path')
        if plot_path:
            print(f"Plot saved to: {plot_path}")
            print(f"File exists: {os.path.exists(plot_path)}")
        else:
            print("No plot generated")
        
        print("\n=== FINAL ANSWER ===")
        print(result.get('final_answer'))
        
    except Exception as e:
        print(f"\nTest FAILED with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_visualization()
