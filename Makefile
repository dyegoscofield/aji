.PHONY: dev down logs migrate shell test psql clean

dev:
	@docker compose up --build

down:
	@docker compose down

logs:
	@docker compose logs -f

migrate:
	@docker compose exec api alembic upgrade head

shell:
	@docker compose exec api bash

test:
	@docker compose exec api pytest tests/ -v

psql:
	@docker compose exec postgres psql -U aji -d aji_db

clean:
	@echo "WARNING: Remove todos os containers e volumes (incluindo dados do banco)."
	@echo "Pressione Ctrl+C para cancelar, ou Enter para continuar."
	@read _
	@docker compose down -v --remove-orphans
