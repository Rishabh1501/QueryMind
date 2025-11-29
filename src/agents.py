from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from src.llm_factory import get_llm
from src.utils import execute_in_docker
from src.data_engine import DataEngine
import json
import os
import pandas as pd
from prompts.prompts import QUERY_GENERATOR_SYSTEM_PROMPT, DUCKDB_QUERY_GENERATOR_SYSTEM_PROMPT, SUMMARIZER_SYSTEM_PROMPT, check_for_jailbreak
import logging
import time

logger = logging.getLogger(__name__)

class Agents:
    def __init__(self):
        self.llm = get_llm()
        self.agent_timings = {}  # Track agent execution times

    def query_generator(self, state):
        """
        Generates Pandas/DuckDB code based on the user query and schema.
        """
        start_time = time.time()
        logger.info("Query Generator: Starting")
        
        messages = state['messages']
        schema_info = state.get('schema_info', {})
        data_path = state.get('data_path')
        
        # Extract the latest user question
        user_query = messages[-1].content
        
        # Security: Check for jailbreak attempts
        is_safe, reason = check_for_jailbreak(user_query)
        if not is_safe:
            logger.warning(f"Jailbreak attempt detected: {reason}")
            return {
                "generated_code": f"# Security Error\nprint('Query rejected: {reason}')",
                "thinking_process": f"Security check failed: {reason}"
            }
        
        # Determine container path for data
        data_filename = os.path.basename(data_path) if data_path else 'data.csv'
        container_path = f"/data/{data_filename}"
        
        # Determine engine type (default to pandas)
        engine_type = schema_info.get("type", "pandas")
        
        if engine_type == "duckdb":
            # For DuckDB, preview might be a list of tuples or similar, need to handle string conversion
            preview_data = schema_info.get("preview", "")
            if hasattr(preview_data, 'to_string'):
                preview_str = preview_data.to_string()
            else:
                preview_str = str(preview_data)

            system_prompt = DUCKDB_QUERY_GENERATOR_SYSTEM_PROMPT.format(
                table_name=schema_info.get("table_name", "data"),
                columns=schema_info.get("columns", []),
                dtypes=schema_info.get("dtypes", []),
                sample_data=preview_str,
                data_path=container_path
            )
        else:
            system_prompt = QUERY_GENERATOR_SYSTEM_PROMPT.format(
                columns=schema_info.get("columns", []),
                dtypes=schema_info.get("dtypes", []),
                sample_data=schema_info.get("preview", pd.DataFrame()).to_string() if 'preview' in schema_info else 'N/A',
                data_path=container_path
            )
        
        # Gemini requires a HumanMessage
        messages_to_send = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Question: {user_query}\n\nFirst, explain your thinking process, then generate the code.")
        ]
        
        response = self.llm.invoke(messages_to_send)
        content = response.content
        
        # Extract thinking process and code
        thinking = ""
        code = ""
        
        # Strategy: Find where actual Python code starts (import statements)
        if "```python" in content:
            # Code is in markdown block
            parts = content.split("```python", 1)
            thinking = parts[0].strip()
            if len(parts) > 1:
                code_block = parts[1].split("```", 1)[0] if "```" in parts[1] else parts[1]
                code = code_block.strip()
        else:
            # No markdown - find first import statement
            lines = content.split("\n")
            code_start_idx = None
            
            for i, line in enumerate(lines):
                stripped = line.strip()
                # Look for Python code indicators
                if stripped.startswith(("import ", "from ", "def ", "class ", "try:", "@")):
                    code_start_idx = i
                    break
            
            if code_start_idx is not None:
                thinking = "\n".join(lines[:code_start_idx]).strip()
                code = "\n".join(lines[code_start_idx:]).strip()
            else:
                # No code found, treat everything as thinking
                thinking = content.strip()
                code = ""
        
        # Clean up code (remove markdown if any remains)
        code = code.replace("```python", "").replace("```", "").strip()
        
        # Validate: ensure code doesn't start with thinking text
        if code and not code.startswith(("import", "from", "def", "class", "try", "@", "#")):
            # Code still has preamble, try to find first real line
            code_lines = code.split("\n")
            for i, line in enumerate(code_lines):
                if line.strip().startswith(("import", "from", "def", "class", "try")):
                    code = "\n".join(code_lines[i:]).strip()
                    break
        
        logger.info(f"Extracted: {len(thinking)} chars thinking, {len(code)} chars code")
        
        # Track execution time
        elapsed = time.time() - start_time
        self.agent_timings['query_generator'] = elapsed
        logger.info(f"Query Generator: Completed in {elapsed:.2f}s")
        
        return {"generated_code": code, "thinking_process": thinking}

    def code_executor(self, state):
        """
        Executes the generated code in Docker.
        """
        start_time = time.time()
        logger.info("Code Executor: Starting")
        
        code = state['generated_code']
        data_path = state['data_path']
        
        result = execute_in_docker(code, data_path)
        
        elapsed = time.time() - start_time
        self.agent_timings['code_executor'] = elapsed
        logger.info(f"Code Executor: Completed in {elapsed:.2f}s")
        
        return {"execution_result": result}

    def validator(self, state):
        """
        Validates the execution result.
        """
        start_time = time.time()
        logger.info("Validator: Starting")
        
        result = state['execution_result']
        
        if result['success']:
            # Simple validation: check if output is not empty
            if not result['output'].strip():
                validation_error = "Execution succeeded but produced no output."
            else:
                validation_error = None
        else:
            validation_error = f"Execution failed: {result['error']}"
        
        elapsed = time.time() - start_time
        self.agent_timings['validator'] = elapsed
        logger.info(f"Validator: Completed in {elapsed:.2f}s")
        
        return {"validation_error": validation_error}

    def summarizer(self, state):
        """
        Summarizes the result for the user.
        """
        start_time = time.time()
        logger.info("Summarizer: Starting")
        
        messages = state['messages']
        user_query = messages[-1].content
        execution_result = state['execution_result']
        validation_error = state.get('validation_error')
        
        if validation_error:
            final_answer = f"I encountered an error while analyzing the data: {validation_error}"
        else:
            output = execution_result['output']
            
            system_prompt = SUMMARIZER_SYSTEM_PROMPT.format(
                user_query=user_query,
                output=output
            )
            
            response = self.llm.invoke([SystemMessage(content=system_prompt)])
            final_answer = response.content
        
        elapsed = time.time() - start_time
        self.agent_timings['summarizer'] = elapsed
        logger.info(f"Summarizer: Completed in {elapsed:.2f}s")
        
        return {"final_answer": final_answer}
    
    # ===== PHASE 2: PRIORITY AGENTS =====
    
    def query_classifier(self, state):
        """
        Classifies the user query to optimize routing.
        Returns query_type: analytical, visualization, comparison, summary, or trend
        """
        start_time = time.time()
        logger.info("Query Classifier: Starting")
        
        user_query = state['messages'][-1].content
        
        prompt = f"""Classify this data analysis query into ONE category:
- analytical: Numerical computation ("what is total revenue?")
- visualization: Requesting charts/graphs ("show me a bar chart")
- comparison: Comparing groups ("Q3 vs Q4")
- summary: Dataset overview ("describe the data")
- trend: Time-series analysis ("sales over time")

Query: {user_query}

Respond with ONLY the category name."""
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            query_type = response.content.strip().lower()
            
            # Validate response
            valid_types = ['analytical', 'visualization', 'comparison', 'summary', 'trend']
            if query_type not in valid_types:
                query_type = 'analytical'  # Default
            
            elapsed = time.time() - start_time
            self.agent_timings['query_classifier'] = elapsed
            logger.info(f"Query Classifier: {query_type} in {elapsed:.2f}s")
            
            return {"query_type": query_type}
        except Exception as e:
            logger.error(f"Query classifier error: {e}")
            return {"query_type": "analytical"}  # Fallback
    
    def insight_generator(self, state):
        """
        Generates proactive follow-up insights after analysis.
        """
        start_time = time.time()
        logger.info("Insight Generator: Starting")
        
        user_query = state['messages'][-1].content
        final_answer = state.get('final_answer', '')
        
        prompt = f"""Based on this data analysis query and result, suggest 3 insightful follow-up questions the user might want to explore.

Original Query: {user_query}
Result: {final_answer[:500]}...

Provide 3 follow-up questions as a numbered list. Be specific and actionable."""
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            suggestions = response.content.strip()
            
            elapsed = time.time() - start_time
            self.agent_timings['insight_generator'] = elapsed
            logger.info(f"Insight Generator: Completed in {elapsed:.2f}s")
            
            return {"suggested_insights": suggestions}
        except Exception as e:
            logger.error(f"Insight generator error: {e}")
            return {"suggested_insights": ""}  # Fallback
    
    def anomaly_detector(self, state):
        """
        Detects anomalies and outliers in the dataset.
        """
        start_time = time.time()
        logger.info("Anomaly Detector: Starting")
        
        schema_info = state.get('schema_info', {})
        
        anomalies = []
        
        # Check for unexpected issues in schema
        if 'missing_values' in schema_info:
            missing = schema_info['missing_values']
            if missing:
                anomalies.append(f"⚠️ Missing data detected in {len(missing)} columns")
        
        # Note: Full anomaly detection requires access to dataframe
        # This is a simplified version that works with schema info
        
        elapsed = time.time() - start_time
        self.agent_timings['anomaly_detector'] = elapsed
        logger.info(f"Anomaly Detector: Completed in {elapsed:.2f}s")
        
        return {"anomalies": anomalies}
    
    def query_optimizer(self, state):
        """
        Reviews generated code for optimization opportunities.
        """
        start_time = time.time()
        logger.info("Query Optimizer: Starting")
        
        code = state.get('generated_code', '')
        
        suggestions = []
        
        # Check for common inefficiencies
        if 'iterrows()' in code:
            suggestions.append("Consider using vectorized operations instead of iterrows()")
        
        if '.apply(' in code and 'lambda' in code:
            suggestions.append("Vectorized operations may be faster than apply() with lambda")
        
        # Check for chained indexing
        if code.count('[') > code.count('.loc[') + code.count('.iloc['):
            suggestions.append("Use .loc[] or .iloc[] to avoid chained indexing warnings")
        
        elapsed = time.time() - start_time
        self.agent_timings['query_optimizer'] = elapsed
        logger.info(f"Query Optimizer: Found {len(suggestions)} suggestions in {elapsed:.2f}s")
        
        return {"optimization_suggestions": suggestions}
    
    def explanation_agent(self, state):
        """
        Provides educational explanation of the generated code.
        """
        start_time = time.time()
        logger.info("Explanation Agent: Starting")
        
        code = state.get('generated_code', '')
        
        if not code or len(code.strip()) == 0:
            return {"code_explanation": ""}
        
        prompt = f"""Explain this Pandas code in simple terms for someone learning data analysis.
Break it down step-by-step.

Code:
```python
{code[:500]}  # First 500 chars
```

Provide a concise explanation (3-5 sentences)."""
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            explanation = response.content.strip()
            
            elapsed = time.time() - start_time
            self.agent_timings['explanation_agent'] = elapsed
            logger.info(f"Explanation Agent: Completed in {elapsed:.2f}s")
            
            return {"code_explanation": explanation}
        except Exception as e:
            logger.error(f"Explanation agent error: {e}")
            return {"code_explanation": ""}  # Fallback
    
    def multi_step_planner(self, state):
        """
        Breaks down complex queries into multiple steps.
        """
        start_time = time.time()
        logger.info("Multi-Step Planner: Starting")
        
        user_query = state['messages'][-1].content
        query_type = state.get('query_type', 'analytical')
        
        # Only activate for comparison or complex queries
        if query_type not in ['comparison', 'trend']:
            return {"execution_plan": None}
        
        prompt = f"""This query might require multiple analysis steps:

Query: {user_query}

Break this into 2-3 sequential steps. Each step should be a specific data operation.
Format as a numbered list.

If the query is simple and doesn't need breakdown, respond with "SINGLE_STEP"."""
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            plan = response.content.strip()
            
            if "SINGLE_STEP" in plan.upper():
                plan = None
            
            elapsed = time.time() - start_time
            self.agent_timings['multi_step_planner'] = elapsed
            logger.info(f"Multi-Step Planner: Completed in {elapsed:.2f}s")
            
            return {"execution_plan": plan}
        except Exception as e:
            logger.error(f"Multi-step planner error: {e}")
            return {"execution_plan": None}  # Fallback
