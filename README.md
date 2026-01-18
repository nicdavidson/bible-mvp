# BibleMVP

A free, open-source Bible study platform with cross-resource linking and word-level Hebrew/Greek study.

## Features

- **Bible Text**: BSB (default), WEB, and KJV translations (93,000+ verses)
- **Word-Level Alignment**: Click any word in BSB to see the original Hebrew/Greek with Strong's definitions (724,000+ alignments)
- **Interlinear Display**: Toggle to show Hebrew (OT) and Greek (NT) text with glosses
- **Cross-References**: 41,000+ entries from Treasury of Scripture Knowledge
- **Commentary**: Matthew Henry's Concise Commentary (65/66 books)
- **Notes**: Personal notes saved locally
- **Search**: Full-text search with Strong's number support (e.g., G26 for agape)
- **Dark Mode**: Easy on the eyes for evening study
- **PWA**: Installable, works offline

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: Alpine.js + vanilla CSS
- **Database**: SQLite with FTS5 full-text search
- **Deployment**: Fly.io with persistent volume for database

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn backend.main:app --reload

# Open http://localhost:8000
```

## Deployment (Fly.io)

The app deploys to Fly.io with a persistent volume for the SQLite database:

```bash
# Deploy
fly deploy

# The database is stored on a persistent volume mounted at /data
# See fly.toml for configuration
```

Note: The SQLite database (~200MB) is too large for GitHub. It's stored on Fly.io's persistent volume and included in the Docker image during deployment.

## Data Sources

| Source | License | Description |
|--------|---------|-------------|
| [Berean Standard Bible](https://berean.bible) | CC-BY 4.0 | Primary translation with word-level alignments |
| [Clear-Bible Alignments](https://github.com/Clear-Bible/Alignments) | CC-BY 4.0 | Hebrew/Greek to English word alignments |
| [Open Bibles](https://github.com/seven1m/open-bibles) | Public Domain | WEB and KJV translations |
| [STEPBible](https://github.com/STEPBible/STEPBible-Data) | CC-BY 4.0 | Hebrew/Greek interlinear data with Strong's |
| [OpenBible.info](https://www.openbible.info/labs/cross-references/) | CC-BY | Cross-references |
| Matthew Henry's Commentary | Public Domain | Commentary (1706) |

## License

MIT
