FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY . .

# Create necessary directories
RUN mkdir -p /var/log/task-manager /app/data

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "-m", "backend.main"]
