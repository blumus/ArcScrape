# backend/Dockerfile
# Use an official Python runtime as a parent image
FROM python:3.13-slim-bookworm

# Set the working directory in the container
WORKDIR /app/backend

# Install system dependencies if needed (e.g., for some Python packages)
RUN apt update && apt install -y \
     build-essential \
     git \
     procps \
     iputils-ping \
     netcat-traditional \
     telnet \
     curl \
     unzip \
     && rm -rf /var/lib/apt/lists/*

# Install AWS CLI with architecture detection
RUN ARCH=$(dpkg --print-architecture) && \
    echo "Detected architecture: $ARCH" && \
    if [ "$ARCH" = "amd64" ]; then \
        AWS_CLI_ARCH="x86_64"; \
    elif [ "$ARCH" = "arm64" ]; then \
        AWS_CLI_ARCH="aarch64"; \
    else \
        echo "Unsupported architecture: $ARCH" && exit 1; \
    fi && \
    echo "Installing AWS CLI for $AWS_CLI_ARCH" && \
    curl "https://awscli.amazonaws.com/awscli-exe-linux-${AWS_CLI_ARCH}.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install && \
    rm -rf aws awscliv2.zip && \
    aws --version

# Copy the requirements file into the container
COPY backend/requirements.txt backend/requirements-dev.txt ./

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt
RUN pip install aws-list-all

# Copy the rest of your application code (this will be mounted by docker-compose,
# but it's good practice for standalone builds or if not using remote containers)
COPY . ..

# Expose the port your FastAPI application will run on
EXPOSE 8000

# Command to run your application (this can be overridden by docker-compose)
# For development, you might run it with auto-reload:
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]