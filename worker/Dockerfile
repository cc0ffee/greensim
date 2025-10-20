# Use a lightweight Python image
FROM python:3.12-alpine

# Set working directory
WORKDIR /app

# Install build dependencies (needed for some packages like pandas)
RUN apk add --no-cache build-base

# Copy requirements file
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# Run the worker script
CMD ["python", "worker.py"]
