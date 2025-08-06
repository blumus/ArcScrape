# CloudCulate

A FastAPI-based application with MongoDB backend, designed for development using Docker containers and VS Code dev containers.

## Project Structure

```
.
├── .devcontainer/
│   └── devcontainer.json          # VS Code dev container configuration
├── backend/
│   ├── Dockerfile                 # Backend container definition
│   └── requirements.txt           # Python dependencies
├── frontend/                      # Frontend directory (to be implemented)
├── docker-compose.yml             # Multi-container application setup
└── README.md                      # This file
```

## Quick Start

### Prerequisites

- [Docker](https://www.docker.com/get-started) and Docker Compose
- [Visual Studio Code](https://code.visualstudio.com/) with the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

### Development Setup

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd ArcScrape
   ```

2. **Open in VS Code Dev Container:**
   - Open the project in VS Code
   - When prompted, click "Reopen in Container" or use `Ctrl+Shift+P` → "Dev Containers: Reopen in Container"
   - VS Code will automatically build and start the development environment

3. **Manual Docker setup (alternative):**
   ```bash
   docker-compose up -d
   ```

## Services

### Backend (FastAPI)
- **Port:** 8000
- **Framework:** FastAPI with Uvicorn
- **Database:** MongoDB integration via PyMongo
- **Development:** Hot reload enabled

### MongoDB
- **Port:** 27017
- **Image:** Official MongoDB latest
- **Data persistence:** Enabled via Docker volumes

## Environment Variables

The application uses the following environment variables:

- `MONGO_URI`: MongoDB connection string (default: `mongodb://mongodb:27017/cloudculate`)

## Development

### Running the Application

Once the dev container is running:

```bash
# The FastAPI server should start automatically
# If not, run manually:
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Access the application:
- **API:** http://localhost:8000
- **Interactive API docs:** http://localhost:8000/docs
- **MongoDB:** localhost:27017

### Installed Development Tools

The dev container includes:
- Python 3.13
- FastAPI and Uvicorn
- MongoDB Python driver (PyMongo)
- VS Code extensions for Python development
- Code formatting and linting tools

### Adding Dependencies

Add new Python packages to [`backend/requirements.txt`](backend/requirements.txt) and rebuild the container:

```bash
# If using dev container, rebuild:
# Ctrl+Shift+P → "Dev Containers: Rebuild Container"

# Or manually:
docker-compose down
docker-compose up --build
```

## Database

MongoDB is configured with persistent storage. Data will persist between container restarts via the `mongo_data` volume.

## VS Code Extensions

The dev container automatically installs:
- Python support and IntelliSense
- Docker integration
- GitHub Copilot
- Code formatting (Black, Flake8)
- Type checking (MyPy)

## Troubleshooting

### Container Issues
```bash
# View logs
docker-compose logs dev_env
docker-compose logs mongodb

# Restart services
docker-compose restart

# Clean rebuild
docker-compose down -v
docker-compose up --build
```

### MongoDB Connection
```bash
# Test MongoDB connection from within the dev container
mongosh mongodb://mongodb:27017/cloudculate
```

## Contributing

1. Make changes in the mounted volume (`/app` in container = `./backend` on host)
2. Changes are automatically synced and the server reloads
3. Test your changes using the FastAPI docs at http://localhost:8000/docs

## AWS Credentials Setup 🔑
This project requires AWS credentials to interact with cloud services.

### Why Read-Only?
For security, we strongly recommend using read-only access. This follows the Principle of Least Privilege, limiting the application's permissions to only what's necessary to read data.

### Configuration
Provide AWS credentials (Access Key ID, Secret Access Key, Region) for a read-only IAM user. Configure these via:

Environment Variables: (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION)

Never hardcode credentials.
## License

This project is licensed under the MIT License.

```
MIT License

Copyright (c) 2025 Baruch Leiman 

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
---