module.exports = {
  apps: [
    {
      name: 'api',
      cwd: './apps/api',
      script: './.venv/bin/uvicorn',
      args: 'app.main:app --host 0.0.0.0 --port 8000',
      interpreter: 'none',
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: 'development',
        PYTHONUNBUFFERED: '1',
      },
      env_production: {
        NODE_ENV: 'production',
        PYTHONUNBUFFERED: '1',
      },
    },
    {
      name: 'ai-orchestrator',
      cwd: './apps/ai-orchestrator',
      script: './.venv/bin/uvicorn',
      args: 'app.main:app --host 0.0.0.0 --port 8001',
      interpreter: 'none',
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: 'development',
        PYTHONUNBUFFERED: '1',
      },
      env_production: {
        NODE_ENV: 'production',
        PYTHONUNBUFFERED: '1',
      },
    },
    {
      name: 'celery-worker',
      cwd: './apps/api',
      script: './.venv/bin/celery',
      args: '-A app.workers.celery_app worker --loglevel=info --concurrency=2 -Q documents',
      interpreter: 'none',
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: 'development',
        PYTHONUNBUFFERED: '1',
      },
      env_production: {
        NODE_ENV: 'production',
        PYTHONUNBUFFERED: '1',
      },
    },
    {
      name: 'web',
      cwd: './apps/web',
      script: 'npm',
      args: 'run dev',
      interpreter: 'none',
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: 'development',
        PORT: 3000,
      },
      env_production: {
        NODE_ENV: 'production',
        PORT: 3000,
        args: 'run start',
      },
    },
  ],
};

