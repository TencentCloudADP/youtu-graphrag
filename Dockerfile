# 1. Use an official Python base image with slim variant to reduce image size
FROM python:3.10

# 2. Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 3. Install system dependencies (including Java for Apache Tika)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        default-jre \
        antiword \
        libreoffice-writer \
        libreoffice-calc && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 4. Create and set working directory
WORKDIR /youtu_graphrag

# 5. Copy project files
COPY . /youtu_graphrag/

# 6. Make scripts executable
RUN chmod +x start.sh

# 7. Setup environment. If using Chinese mode, the corresponding Chinese database should be used here.
RUN pip install -r requirements.txt && python -m spacy download en_core_web_lg

# 8. Expose application port
EXPOSE 8000

# 9. Set the default command to start the application
CMD ["sh", "-c", "./start.sh"]