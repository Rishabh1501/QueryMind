import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.graph import create_graph
from src.data_engine import DataEngine
from src.utils import load_config
from langchain_core.messages import HumanMessage

def test_flow():
    print("Starting verification test...")
    
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
    print("Data loaded. Schema info obtained.")
    
    # Create Graph
    graph = create_graph()
    print("Graph created.")
    
    # Define Query
    query = "What is the total stock available?"
    print(f"Query: {query}")
    
    # Initial State
    initial_state = {
        "messages": [HumanMessage(content=query)],
        "data_path": data_path,
        "schema_info": schema_info,
        "generated_code": "",
        "execution_result": {},
        "validation_error": None,
        "final_answer": ""
    }
    
    # Invoke Graph
    print("Invoking graph...")
    try:
        result = graph.invoke(initial_state)
        print("Graph execution completed.")
        
        print("\n--- Results ---")
        print(f"Generated Code:\n{result.get('generated_code')}")
        print(f"Execution Output:\n{result.get('execution_result', {}).get('output')}")
        print(f"Final Answer:\n{result.get('final_answer')}")
        
        if result.get('final_answer'):
            print("\nVerification SUCCESS!")
        else:
            print("\nVerification FAILED: No final answer.")
            
    except Exception as e:
        print(f"\nVerification FAILED with error: {e}")

if __name__ == "__main__":
    test_flow()
