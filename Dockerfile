# Multi-stage build for faster builds and smaller image
FROM langchain/langgraph-api:3.11 as base

# Create a separate stage for dependencies
FROM base as deps

# Set environment variables to force CPU usage
ENV CUDA_VISIBLE_DEVICES=""
ENV TORCH_USE_CUDA_DSA="0"
ENV TRANSFORMERS_OFFLINE="1"

COPY pyproject.toml uv.lock ./
RUN PYTHONDONTWRITEBYTECODE=1 pip install --no-cache-dir -c /api/constraints.txt uv
# Install CPU-only PyTorch first to avoid GPU dependencies
RUN uv pip install --system --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
RUN uv pip install --system --no-cache-dir -r pyproject.toml

# Final stage with application code
FROM base as final

# Set environment variables to force CPU usage in final image
ENV CUDA_VISIBLE_DEVICES=""
ENV TORCH_USE_CUDA_DSA="0"
ENV TRANSFORMERS_OFFLINE="1"

# Copy pre-installed dependencies from deps stage
COPY --from=deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Add application code
ADD . /deps/DHURBA_FURNITURE_AGENT

# Install the local package only
RUN PYTHONDONTWRITEBYTECODE=1 pip install --no-cache-dir --no-deps -e /deps/DHURBA_FURNITURE_AGENT

ENV LANGSERVE_GRAPHS='{"dhurba_furniture_agent": "/deps/DHURBA_FURNITURE_AGENT/agent/agent.py:agent"}'

# Ensure user deps didn't inadvertently overwrite langgraph-api
RUN mkdir -p /api/langgraph_api /api/langgraph_runtime /api/langgraph_license && \
    touch /api/langgraph_api/__init__.py /api/langgraph_runtime/__init__.py /api/langgraph_license/__init__.py
RUN PYTHONDONTWRITEBYTECODE=1 pip install --no-cache-dir --no-deps -e /api

# Remove pip from final image
RUN pip uninstall -y pip setuptools wheel && \
    rm -rf /usr/local/lib/python*/site-packages/pip* /usr/local/lib/python*/site-packages/setuptools* /usr/local/lib/python*/site-packages/wheel* && \
    find /usr/local/bin -name "pip*" -delete

WORKDIR /deps/DHURBA_FURNITURE_AGENT