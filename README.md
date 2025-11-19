# Vancouver Real Estate Data Scraper

A headless scraper for collecting real estate listings data from Zealty.ca covering Metro Vancouver. Uses direct API calls to efficiently gather thousands of listings across different categories.

## Features

- **Direct API Integration**: No UI clicking required after login—issues direct HTTP POST requests to the backend
- **Grid-Based Fetching**: Splits Metro Vancouver into a 3×3 grid to bypass the 500-row API limit
- **Three Data Categories**:
  - For Sale (Active listings, ordered by recent listing/price changes)
  - Solds (Last 12 months)
  - Expired (Last 30 days)
- **Timestamped Runs**: Each scrape creates a new timestamped folder under `data/` for historical tracking
- **Automatic Deduplication**: Removes duplicate MLS listings across grid boxes

## Setup

### 1. Install Dependencies

This project uses `uv` for dependency management. Install dependencies with:

```bash
uv sync
```

Or run directly with inline dependencies:

```bash
uv run --with playwright --with python-dotenv zealty_scraper_multi.py
```

### 2. Configure Environment Variables

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your Zealty.ca credentials:
   ```env
   ZEALTY_USERNAME=your.email@example.com
   ZEALTY_PASSWORD=your_password_here
   ```

   **Important**: The `.env` file is already in `.gitignore` and will never be committed to version control.

### 3. Install Playwright Browsers

Playwright requires browser binaries. Install them once:

```bash
playwright install chromium
```

## Usage

Run the scraper:

```bash
uv run --with playwright --with python-dotenv zealty_scraper_multi.py
```

The scraper will:
1. Log in to Zealty.ca using your credentials
2. Load the map page to establish a session
3. Issue 27 direct API calls (9 grid boxes × 3 categories)
4. Save results to `data/run-YYYY-MM-DD_HH-MM-SS/`

### Output

Each run creates three CSV files in a timestamped directory:

```
data/
└── run-2025-11-18_17-54-48/
    ├── for_sale_today.csv       (3,533 listings)
    ├── solds_last_12_months.csv (3,556 listings)
    └── expired_last_30_days.csv (2,838 listings)
```

### CSV Columns

Each CSV contains the following columns:

| Column | Description |
|--------|-------------|
| `MLS_Number` | Unique MLS listing number |
| `Latitude` | Property latitude |
| `Longitude` | Property longitude |
| `Date` | Listing/sale/expiry date |
| `Unknown1` | Additional field (varies) |
| `Address` | Street address |
| `Neighborhood` | Neighborhood name |
| `Price` | Price in thousands (CAD) |
| `Description` | Property description (truncated) |
| `Property_Type` | Type (Single Family, Condo, Townhouse, etc.) |
| `Stories` | Number of stories |
| `Unknown2` | Additional field |
| `Bedrooms` | Number of bedrooms |
| `Bathrooms` | Number of bathrooms |
| `Unknown3` | Square footage |
| `Unknown4` | Lot frontage |
| `Unknown5` | Lot dimensions |

## How It Works

### Authentication
- Logs in via Playwright to establish a valid session
- Session cookies are automatically used for subsequent API requests

### Token Generation
The API requires a token `s` parameter for each request. This is computed as:
```python
s = MD5(sql_query)
```

### Geographic Coverage
Metro Vancouver is divided into a 3×3 grid:
- **Latitude**: 49.0 to 49.5
- **Longitude**: -123.3 to -122.5

Each grid box is queried independently, allowing us to collect up to 4,500 listings per category (9 boxes × 500 limit).

### API Parameters
Each request includes:
- `sql`: SQL query with lat/lon bounds and property filters
- `sold`: Category filter (`active`, `sold`, or `expired`)
- `from`: Always `dmap` (map interface)
- `s`: MD5 token of the SQL query

## Files

- `zealty_scraper_multi.py` - Main scraper script
- `.env` - Your credentials (not in git)
- `.env.example` - Template for credentials
- `.gitignore` - Excludes `.env` and other sensitive files
- `data/` - Output directory for all runs (committed to git)

## Notes

- The scraper runs in headless mode by default
- Each run takes approximately 2-3 minutes
- The 500-row API limit per query is bypassed using geographic grid splitting
- All CSV files use UTF-8 encoding

## Overview

This scraper logs into Zealty.ca, navigates to the map interface, and intercepts the internal API calls (`svcFetchDB.php`) used to fetch listing data. The captured data is then saved to a CSV file for analysis.

## How It Works

1. **Login**: Uses Playwright to automate login at `https://www.zealty.ca/sign-in`
2. **API Interception**: Captures network requests to `bcrealestatemap.ca/svcFetchDB.php` which contains:
   - Session token (`s` parameter)
   - SQL query with geographic bounds
   - Listing data in JSON format
3. **Data Extraction**: Parses the JSON response containing listing details
4. **CSV Export**: Saves all captured listings to `listings.csv`

## Prerequisites

- Python 3.8+
- [uv](https://github.com/astral-sh/uv) package manager (recommended)
- Valid Zealty.ca account credentials

## Installation

1. Clone or download this repository
2. Create a `.env` file in the project directory:

```bash
ZEALTY_USERNAME=your_email@example.com
ZEALTY_PASSWORD=your_password
```

3. Install Playwright browsers (first time only):

```bash
uv run --with playwright playwright install chromium
```

## Usage

Run the scraper:

```bash
uv run --with playwright --with python-dotenv zealty_scraper.py
```

The script will:
- Log in to Zealty.ca
- Navigate to the map interface
- Wait for listing data to load
- Interact with the map to trigger additional API calls
- Save all captured listings to `listings.csv`

## Output Format

The script generates a `listings.csv` file with the following columns:

- **MLS_Number**: Multiple Listing Service number
- **Latitude**: Geographic latitude
- **Longitude**: Geographic longitude
- **Date**: Listing date
- **Address**: Property address
- **Neighborhood**: Neighborhood name
- **Price**: Listing price
- **Description**: Property description
- **Property_Type**: Type of property (e.g., Townhouse, Condo)
- **Stories**: Number of stories
- **Bedrooms**: Number of bedrooms
- **Bathrooms**: Number of bathrooms
- Additional fields (Unknown1-5): Other data fields from the API

## Technical Details

### API Endpoints

The scraper intercepts calls to:
- `https://bcrealestatemap.ca/svcFetchDB.php` - Main listing data endpoint
- `https://bcrealestatemap.ca/svcGetInfoDB.php` - Additional property info

### Authentication

- Uses NextAuth.js session-based authentication
- Session token is automatically managed by the browser
- The `s` parameter in API calls is a session-specific token

### Data Structure

The API returns data in the following format:

```json
{
  "columns": ["field1", "field2", ...],
  "rows": [
    ["value1", "value2", ...],
    ...
  ],
  "error": {"code": 0, "message": "", "query": ""}
}
```

## Limitations

- Only captures listings visible in the current map view
- Session tokens are temporary and expire
- The script runs in headless mode (no visible browser window)
- Geographic bounds are determined by the default map view

## Troubleshooting

### No listings captured

- Verify your credentials in the `.env` file
- Check if the website structure has changed
- Try increasing the wait times in the script

### Login fails

- Ensure your Zealty.ca account is active
- Check for CAPTCHA or additional verification requirements
- Verify the login form selectors are still valid

### Browser not found

Run:
```bash
uv run --with playwright playwright install chromium
```

## Files

- `zealty_scraper.py` - Main scraper script
- `.env` - Credentials (not committed to git)
- `listings.csv` - Output file with scraped data
- `inspect_api.py` - Development/debugging script for API inspection

## Legal & Ethical Considerations

- Ensure you have permission to scrape data from Zealty.ca
- Respect the website's terms of service and robots.txt
- Use rate limiting to avoid overloading the server
- Only use the data for personal, non-commercial purposes unless authorized

## License

This project is provided as-is for educational purposes.
