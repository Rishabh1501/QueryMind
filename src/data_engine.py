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
        """
        if self.engine_type == "duckdb":
            try:
                # Execute SQL query
                result_df = self.connection.execute(query).fetchdf()
                return {
                    "success": True, 
                    "dataframe": result_df,
                    "row_count": len(result_df),
                    "preview": result_df.head()
                }
            except Exception as e:
                return {"success": False, "error": str(e)}
        else:
            # For Pandas, the execution happens in the agent's generated code (in Docker)
            # This method might be unused for Pandas mode or used for simple validations
            return {"success": False, "error": "Pandas execution should be handled by the agent generated code."}
