FROM python:3.13-slim

WORKDIR /app

# Copy requirements first for better caching
COPY pyproject.toml uv.lock ./

# Install uv for faster dependency management
RUN pip install uv

# Install dependencies
RUN uv sync --frozen

# Copy application code
COPY . .

# Expose port for HTTP transport
EXPOSE 8000

# Set environment variable for port
ENV PORT=8000

# Run the FastMCP server
CMD ["uv", "run", "python", "-m", "src.index"]
