FROM python:3.9-slim

WORKDIR /app

# Install pandas and openpyxl for data processing
RUN pip install pandas openpyxl duckdb matplotlib seaborn

# Copy data directory to container (will be mounted at runtime usually, but good to have structure)
# We will mount the data directory to /data

CMD ["python", "script.py"]
