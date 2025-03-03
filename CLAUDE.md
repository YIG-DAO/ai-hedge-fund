# Reindustrialization Newsletter Development Guidelines

## Commands
- Run main app: `poetry run python src/main.py --ticker SYMBOL [--show-reasoning]`
- Run workflow: `poetry run python workflow.py` or `bash workflow.sh`
- Docker: `docker-compose up`
- Install dependencies: `poetry install`
- Format code: `poetry run black .`
- Sort imports: `poetry run isort .`
- Lint: `poetry run flake8`
- Test: `poetry run pytest`

## Style Guidelines
- **Imports**: standard lib → third-party → local (tools → type annotations)
- **Type Annotations**: Use TypedDict for structured data, annotate all functions
- **Error Handling**: Try/except with specific exceptions and fallback values
- **Naming**: snake_case for variables/functions, PascalCase for classes
- **Code Structure**: Agent-based architecture with modular design
- **Documentation**: Docstrings for functions, comments for complex logic
- **Architecture**: LangGraph StateGraph for agent workflow management
- **Environment**: Configure via environment variables (.env file)
- **Output**: JSON (machine-readable), HTML reports (human consumption)