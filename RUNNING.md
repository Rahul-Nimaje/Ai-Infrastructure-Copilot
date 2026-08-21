# Running AI Infrastructure Copilot

This guide outlines how to run the backend API and the frontend web application in both Docker containers and native local development modes.

---

## Prerequisites
Ensure you have the following installed:
* [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/install/)
* [Node.js](https://nodejs.org/) (v18+ or v20+)
* [Python](https://www.python.org/) (v3.11+)

---

## Method A: Running via Docker (Recommended)

You can launch the complete backend stack (PostgreSQL + Redis + Backend API) using Docker Compose.

### 1. Build and Run the Stack
Run the following command from the project root:
```bash
# Use 'sudo' if your user is not in the docker group
docker compose -f infra/docker/docker-compose.local.yml up --build -d
```

### 2. Run Database Migrations
Once the database container is healthy, run the Alembic migrations to create the schema and seed the default roles/permissions:
```bash
docker compose -f infra/docker/docker-compose.local.yml exec api alembic upgrade head
```

### 3. Start the Frontend
Since Next.js development is best done locally with hot reloading, run the frontend locally:
```bash
# 1. Install dependencies from the workspace root
npm install

# 2. Run the Next.js development server
npm run dev --workspace=@ai-infra-copilot/web
```
The application will be available at:
* **Frontend UI:** [http://localhost:3000](http://localhost:3000)
* **Backend API:** [http://localhost:8000](http://localhost:8000)

---

## Method B: Native Local Development (No Containerized API)

If you are debugging or modifying the backend code directly, you can run the databases in Docker and the API/Frontend services natively.

### 1. Start Database and Redis Only
Run PostgreSQL and Redis in the background:
```bash
docker compose -f infra/docker/docker-compose.local.yml up postgres redis -d
```

### 2. Set Up and Run the Backend API
Navigate to the `apps/api` folder, initialize the virtual environment, install dependencies, and run the service:
```bash
cd apps/api

# Create virtual environment if you haven't already
python3 -m venv .venv
source .venv/bin/activate

# Install shared packages and app requirements
pip install -e ../../packages/py-shared
pip install -e .

# Run migrations
alembic upgrade head

# Start the development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Set Up and Run the Frontend
Open a new terminal session and run:
```bash
cd apps/web

# Install dependencies (if not done already)
npm install

# Run the Next.js app in development mode
npm run dev
```

---

## Troubleshooting & Verification

### Checking Logs
To stream logs from the docker-compose stack:
```bash
docker compose -f infra/docker/docker-compose.local.yml logs -f
```

### Resetting database data
To tear down the database container and clear Postgres persistent volumes to start fresh:
```bash
docker compose -f infra/docker/docker-compose.local.yml down -v
```

### Seed Credentials
* **Seeded Administrator Login:** `admin` / `ChangeMe123!`
