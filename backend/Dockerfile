# Parent image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# System dependencies 
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file and install Python dependencies
# We do this before copying the whole app to leverage Docker's cache layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of your application code (including knowledge.json)
COPY . .

# 6. Set environment variables (Use AWS Secrets Manager instead for the API Key in production)
ENV PYTHONUNBUFFERED=1

# 7. Expose the port your FastAPI/Flask app runs on
EXPOSE 8080

# 8. Command to run the application
CMD ["python", "app/main.py"]