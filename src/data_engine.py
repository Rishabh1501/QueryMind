import pandas as pd
import duckdb
import os

class DataEngine:
    def __init__(self, config):
        self.engine_type = config.get("data", {}).get("engine", "pandas")
        self.connection = None
        if self.engine_type == "duckdb":
            self.connection = duckdb.connect(database=':memory:')

    def load_data(self, file_path):
        """
        Loads data and returns a preview or schema info.
        For DuckDB, it registers the file as a view.
        For Pandas, it loads the dataframe.
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if self.engine_type == "duckdb":
            table_name = "sales_data"
            if file_ext == ".csv":
                self.connection.execute(f"CREATE OR REPLACE VIEW {table_name} AS SELECT * FROM read_csv_auto('{file_path}')")
            elif file_ext in [".xls", ".xlsx"]:
                # DuckDB doesn't natively support Excel as well as CSV, usually need to convert to CSV or use pandas
                # For simplicity in this hybrid approach, we might load excel with pandas then register
                df = pd.read_excel(file_path)
                self.connection.register(table_name, df)
            
            # Return schema info
            schema_df = self.connection.execute(f"DESCRIBE {table_name}").fetchdf()
            return {
                "type": "duckdb",
                "table_name": table_name,
                "columns": schema_df['column_name'].tolist(),
                "dtypes": schema_df['column_type'].tolist(),
                "preview": self.connection.execute(f"SELECT * FROM {table_name} LIMIT 5").fetchdf()
            }
            
        else: # Pandas
            if file_ext == ".csv":
                df = pd.read_csv(file_path)
            elif file_ext in [".xls", ".xlsx"]:
                df = pd.read_excel(file_path)
            else:
                raise ValueError("Unsupported file format")
            
            return {
                "type": "pandas",
                "dataframe": df,
                "columns": df.columns.tolist(),
                "dtypes": df.dtypes.astype(str).tolist(),
                "preview": df.head()
            }

    def execute_query(self, query):
        """
        Executes a query. 
        If engine is DuckDB, query should be SQL.
        If engine is Pandas, query should be Python/Pandas code.
        
        Wait, the requirement is "Agents generate python pandas query".
        If we use DuckDB, we can still use DuckDB's Python API which is very pandas-like or SQL.
        However, to support 100GB+ data, we MUST use SQL or DuckDB's relation API, NOT pure Pandas on the full dataset.
        
        BUT, the prompt says "generate python pandas query".
        
        Hybrid approach:
        - If small data: Generate Pandas code.
        - If large data (DuckDB): Generate SQL or DuckDB Python API code.
        
        For now, let's stick to the plan: The agent generates code.
        If we are in "DuckDB mode", the agent should be instructed to generate SQL or DuckDB python code.
        
        This method might just be a helper for the VALIDATION agent or initial inspection.
        The actual execution happens in the Docker container.
        
        So this class is mainly for the 'Data Extraction Agent' to understand the schema.
        """
        pass
