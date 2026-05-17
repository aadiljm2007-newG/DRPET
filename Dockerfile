FROM python:3.9-slim

WORKDIR /app

# Install System Dependencies (Crucial for AI/Vision engines like OpenCV)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all the backend logic and models
COPY backend/ ./backend/
COPY *.pt .

# Hugging Face Spaces specifically looks for applications running on port 7860
ENV HOST=0.0.0.0
ENV PORT=7860
ENV PYTHONPATH=/app/backend
EXPOSE 7860

# Boot up the uvicorn server bypassing the main.py hardcoded port
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
