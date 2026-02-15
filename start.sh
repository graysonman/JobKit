#!/bin/bash
set -e

echo "Running database setup..."
python -c "
import subprocess
from app.database import engine, Base
from app.models import *
from app.auth.models import *
from sqlalchemy import inspect

inspector = inspect(engine)
existing = inspector.get_table_names()

if 'users' not in existing:
    print('Fresh database — creating all tables...')
    Base.metadata.create_all(bind=engine)
    subprocess.run(['alembic', 'stamp', 'head'], check=True)
    print('Tables created and alembic stamped to head.')
else:
    print('Existing database — running migrations...')
    subprocess.run(['alembic', 'upgrade', 'head'], check=True)
    print('Migrations complete.')
"

echo "Starting server..."
exec gunicorn app.main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers 2 \
    --bind 0.0.0.0:8000 \
    --graceful-timeout 120 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
