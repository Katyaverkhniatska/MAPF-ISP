# Docker Setup for MAPF-ISP

## Building and Running Tests

### Quick Start
Build and run tests in one command:
```bash
docker compose up --build
```

This will:
1. Build the Docker image
2. Run all unit tests with verbose output
3. Exit (no persistent server needed)

### Build Only
```bash
docker compose build
```

### Run Tests Only (after build)
```bash
docker compose up
```

### Interactive Shell
For debugging or exploring the container:
```bash
docker compose run --rm mapf-isp /bin/bash
```

Then inside the container:
```bash
python -m unittest discover -s tests             # Run tests
python                                           # Interactive Python shell
ls -la /app                                      # Explore contents
```

## Deploying to the Cloud

If you deploy this project to a cloud provider (e.g., for CI/CD):

**Build for different architectures:**
```bash
docker build --platform=linux/amd64 -t myregistry.com/mapf-isp .
docker build --platform=linux/arm64 -t myregistry.com/mapf-isp .
```

**Push to a registry:**
```bash
docker push myregistry.com/mapf-isp
```

For more details, see [Docker's getting started guide](https://docs.docker.com/go/get-started-sharing/).

## Security Notes

- The application runs as a non-privileged user (`appuser`) for security
- `PYTHONDONTWRITEBYTECODE=1` prevents `__pycache__` files in the container
- `.dockerignore` excludes unnecessary files (git, venv, IDE config, etc.)