.PHONY: all deps start rmdb

all: deps start

deps:
	poetry config virtualenvs.in-project true
	poetry install --no-root

start :; poetry run python3 main.py

rmdb :; rm -rf sql.db sql.db-shm sql.db-wal