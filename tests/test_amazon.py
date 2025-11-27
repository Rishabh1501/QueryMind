import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.graph import create_graph
from src.data_engine import DataEngine
from src.utils import load_config
from langchain_core.messages import HumanMessage

def test_amazon_query():
    print("Testing Amazon Sale Report analysis...")
    
    # Load Config
    config = load_config()
    print("Config loaded.")
    
    # Initialize Data Engine
    data_engine = DataEngine(config)
    data_path = os.path.abspath("data/Amazon Sale Report.csv")
    
    if not os.path.exists(data_path):
        print(f"Error: Data file not found at {data_path}")
        return
        
    print(f"Loading data from {data_path}...")
    schema_info = data_engine.load_data(data_path)
    print("Data loaded. Schema info obtained.")
    print(f"Columns: {schema_info.get('columns', [])[:10]}...")  # Show first 10 columns
    
    # Create Graph
    graph = create_graph()
    print("Graph created.")
    
    # Define Query
    query = "Which category has the highest total sales revenue?"
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
        print(f"\nExecution Output:\n{result.get('execution_result', {}).get('output')}")
        print(f"\nFinal Answer:\n{result.get('final_answer')}")
        
    except Exception as e:
        print(f"\nTest FAILED with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_amazon_query()
