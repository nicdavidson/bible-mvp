# BibleMVP

A free, open-source Bible study platform with cross-resource linking.

## Features

- **Bible Text**: WEB and KJV translations (61,000+ verses)
- **Cross-References**: 41,000+ entries from Treasury of Scripture Knowledge
- **Commentary**: Matthew Henry's Concise Commentary (Genesis, Exodus, Leviticus)
- **Notes**: Personal notes saved locally
- **Dark Mode**: Easy on the eyes for evening study
- **Fast Navigation**: Chapter/verse buttons, book autocomplete, verse preview on hover

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: Alpine.js + vanilla CSS
- **Database**: SQLite with FTS5 full-text search

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn backend.main:app --reload

# Open http://localhost:8000
```

## Data Sources (Public Domain)

- Bible text: [Open Bibles](https://github.com/seven1m/open-bibles)
- Cross-references: [OpenBible.info](https://www.openbible.info/labs/cross-references/) (CC-BY)
- Commentary: Matthew Henry's Concise Commentary (1706)

## License

MIT
