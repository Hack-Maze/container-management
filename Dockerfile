
# Stage 1: Build stage
FROM python:3.12-slim as builder

WORKDIR /app

# Copy requirements.txt to the container
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --upgrade setuptools wheel

# Install dependencies
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy the application source code
RUN rm requirements.txt
COPY app.py app.py

# Stage 2: Production stage
FROM python:3.12-slim

WORKDIR /app

# Copy the installed dependencies from the previous stage
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

# Copy the application source code from the previous stage
COPY --from=builder /app/* .

# Expose port 80
EXPOSE 80
 
CMD ["python","app.py"]
