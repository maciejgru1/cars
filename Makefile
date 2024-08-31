tests:
	pytest src/tests
lint:
	ruff format src
	ruff check src
lint_fix:
	ruff check src --fix
format:
	ruff format src
	docformatter --config pyproject.toml --in-place --force-wrap src
run:
	uv run uvicorn src.app:app --lifespan on --reload --app-dir src --host localhost --port 8000
clean:
	for /d /r src\ %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
install:
	uv sync