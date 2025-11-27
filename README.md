- **Visualization Support**: Request charts and graphs - they're generated and displayed automatically
- **Thinking Process**: See the AI's reasoning before code generation for transparency
- **Sandboxed Execution**: All code runs safely inside Docker containers
- **Multi-LLM Support**: Works with Gemini, OpenAI, Claude, or local Ollama models
- **Scalable**: Handles 100GB+ datasets via DuckDB
- **Security**: Built-in prompt injection detection and code validation

## Prerequisites
1. **Python 3.9+**
2. **Docker Desktop** (must be running)
3. **Gemini API Key** (or Ollama for local LLMs)

## Setup

### 1. Install Dependencies
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configure API Key
Create a `.env` file:
```
GOOGLE_API_KEY=your_gemini_api_key_here
```

### 3. Build Docker Image
```bash
docker build -t retail_insights_executor ./docker
```

### 4. Run the Application
```bash
streamlit run app.py
```

## Usage

1. **Upload Data**: Upload CSV or Excel file via sidebar (sample data in `data/` folder)
2. **Ask Questions**:
   - "What is the total sales revenue?"
   - "Which category has the highest revenue?"
   - "Show me a bar chart of stock by category"
   - "Plot the monthly sales trend"

## Configuration

Edit `config.yaml`:
```yaml
llm_provider: google  # Options: google, ollama, openai, anthropic
model_name: gemini-2.5-flash

execution:
  max_parallel_containers: 5
  timeout_seconds: 30

data:
  engine: duckdb  # Use 'duckdb' for 100GB+ data, 'pandas' for smaller files
```

## Architecture

✅ **File Upload Error**: Fixed JSON serialization error when displaying data preview  
✅ **Query Ambiguity**: Improved prompt to clarify revenue vs quantity questions

### New Features
✅ **Graph/Plot Support**: Generate matplotlib visualizations on demand  
✅ **Thinking Process Display**: See AI reasoning before code generation  
✅ **Security Guardrails**: Jailbreak detection + code validation

## Project Structure
```
blend-360-project/
├── app.py                 # Streamlit UI
├── config.yaml           # Configuration
├── requirements.txt
├── prompts/
│   └── prompts.py        # System prompts & security checks
├── src/
│   ├── agents.py         # LangGraph agents
│   ├── graph.py          # State machine definition
│   ├── llm_factory.py    # Multi-LLM support
│   ├── data_engine.py    # Pandas/DuckDB abstraction
│   └── utils.py          # Docker execution + validation
├── docker/
│   └── Dockerfile        # Execution sandbox (Python + pandas + matplotlib)
└── data/                 # Sample datasets
```

## Troubleshooting
- **Docker Error**: Ensure Docker Desktop is running
- **API Error**: Verify API key in `.env` file
- **Large Files**: Switch to `engine: duckdb` in `config.yaml` for datasets over 1GB

## Scalability
For 100GB+ datasets:
1. Set `data.engine: duckdb` in `config.yaml`
2. DuckDB queries CSV/Parquet files directly from disk (no memory loading)
3. Results still returned as Pandas DataFrames to agents

## Security Notes
- All code execution happens in isolated Docker containers
- Containers have no network access
- File system access limited to `/data` (read) and `/output` (write)
- Automatic detection of 15+ jailbreak patterns
- Code scanned for dangerous operations before execution
