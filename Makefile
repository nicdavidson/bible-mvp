.PHONY: setup build build-full dev clean list help cache-stats bundle-sources setup-sources deploy deploy-code

# Default target
help:
	@echo "BibleMVP Development Commands"
	@echo "============================="
	@echo ""
	@echo "  make setup          Download pre-built database (fast, ~30s)"
	@echo "  make build          Build database from sources (incremental)"
	@echo "  make build-full     Rebuild database from scratch (~10-20 min first time)"
	@echo "  make build-offline  Build from cached sources only (no network)"
	@echo "  make dev            Start local dev server"
	@echo "  make list           Show database build status"
	@echo "  make clean          Remove local database"
	@echo ""
	@echo "Deployment:"
	@echo "  make deploy         Build DB + deploy to Fly.io (code + DB)"
	@echo "  make deploy-code    Deploy code only (no DB rebuild)"
	@echo ""
	@echo "Source Data Caching:"
	@echo "  make cache-stats    Show what's cached locally"
	@echo "  make bundle-sources Create sources.tar.zst for file server"
	@echo "  make setup-sources  Download source bundle from file server"
	@echo ""

# Download pre-built database from GitHub Releases
setup:
	@./scripts/setup_db.sh

# Build database from source data (incremental)
build:
	@. .venv/bin/activate 2>/dev/null || true; python scripts/build_db.py

# Full rebuild from scratch
build-full:
	@. .venv/bin/activate 2>/dev/null || true; python scripts/build_db.py --full

# Build from cached sources only (no network)
build-offline:
	@. .venv/bin/activate 2>/dev/null || true; python scripts/build_db.py --skip-network

# Start local dev server
dev:
	@. .venv/bin/activate 2>/dev/null || true; uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Show build status
list:
	@. .venv/bin/activate 2>/dev/null || true; python scripts/build_db.py --list

# Remove database (keeps source data)
clean:
	@rm -f data/bible.db
	@echo "Removed data/bible.db"

# Show source cache statistics
cache-stats:
	@. .venv/bin/activate 2>/dev/null || true; python scripts/source_cache.py

# Bundle all source data for offline builds
# Includes: cached network downloads + BSB data files (not full git repos)
bundle-sources:
	@echo "Creating source data bundle..."
	@mkdir -p data/sources/bsb-data
	@# Copy essential BSB files from the cloned repo (skip .git)
	@if [ -d data/clear-bible/data ]; then \
		cp data/clear-bible/data/sources/WLCM.tsv data/sources/bsb-data/ 2>/dev/null || true; \
		cp data/clear-bible/data/sources/SBLGNT.tsv data/sources/bsb-data/ 2>/dev/null || true; \
		mkdir -p data/sources/bsb-data/targets; \
		cp data/clear-bible/data/eng/targets/BSB/ot_BSB.tsv data/sources/bsb-data/targets/ 2>/dev/null || true; \
		cp data/clear-bible/data/eng/targets/BSB/nt_BSB.tsv data/sources/bsb-data/targets/ 2>/dev/null || true; \
		mkdir -p data/sources/bsb-data/alignments; \
		cp data/clear-bible/data/eng/alignments/BSB/WLCM-BSB-manual.json data/sources/bsb-data/alignments/ 2>/dev/null || true; \
		cp data/clear-bible/data/eng/alignments/BSB/SBLGNT-BSB-manual.json data/sources/bsb-data/alignments/ 2>/dev/null || true; \
	fi
	@# Copy speaker-quotations data (skip .git)
	@if [ -d data/speaker-quotations ]; then \
		mkdir -p data/sources/speaker-quotations; \
		find data/speaker-quotations -name "*.json" -not -path "*/.git/*" -exec cp {} data/sources/speaker-quotations/ \;; \
	fi
	@# Create the tarball
	@if command -v zstd >/dev/null 2>&1; then \
		tar cf - -C data sources alignment cross_references.txt | zstd -T0 -o data/sources.tar.zst; \
		echo "Bundle created: data/sources.tar.zst ($$(du -h data/sources.tar.zst | cut -f1))"; \
	else \
		tar czf data/sources.tar.gz -C data sources alignment cross_references.txt; \
		echo "Bundle created: data/sources.tar.gz ($$(du -h data/sources.tar.gz | cut -f1))"; \
	fi

# Download source bundle from file server
# Set SOURCES_URL to your file server URL, e.g.:
#   SOURCES_URL=http://myserver/bible/sources.tar.zst make setup-sources
setup-sources:
	@if [ -z "$(SOURCES_URL)" ]; then \
		echo "Usage: SOURCES_URL=http://your-server/sources.tar.zst make setup-sources"; \
		echo ""; \
		echo "Or place sources.tar.zst in data/ and run:"; \
		echo "  cd data && zstd -d sources.tar.zst -c | tar xf -"; \
		exit 1; \
	fi
	@echo "Downloading source bundle from $(SOURCES_URL)..."
	@curl -fSL --progress-bar "$(SOURCES_URL)" -o data/sources.tar.zst
	@echo "Unpacking..."
	@cd data && zstd -d sources.tar.zst -c | tar xf -
	@echo "Done! Source data ready. Run 'make build' to build the database."

# Git hash for automatic service worker cache busting
SW_VERSION := $(shell git rev-parse --short HEAD)

# Full deploy: rebuild DB, then deploy to Fly (code + fresh DB)
deploy: build
	@echo ""
	@echo "Generating manifest..."
	@. .venv/bin/activate 2>/dev/null || true; python scripts/build_db.py --manifest
	@echo ""
	@echo "Deploying to Fly.io (SW version: $(SW_VERSION))..."
	fly deploy --build-arg SW_VERSION=$(SW_VERSION)
	@echo ""
	@echo "Deploy complete! Entrypoint will sync DB to volume on startup."

# Code-only deploy (skip DB rebuild, use whatever DB is on the volume)
deploy-code:
	fly deploy --build-arg SW_VERSION=$(SW_VERSION)
