# data/SOURCES.md

## Dataset Origins and Compliance

RUBICON uses only the following data sources:

### 1. Controlled synthetic drill data

All experiments (R01–R21) use purpose-built synthetic fixtures:
- `rubicon-lab/tracked.txt` — synthetic text file, no real content
- `rubicon-lab/db/state.sqlite` — synthetic SQLite events table
- `rubicon-lab/fixtures/http/events.jsonl` — synthetic HTTP event log
- `rubicon-lab/ignored.txt` — synthetic ignored file

No personal, confidential, company, or social-media data is used.

### 2. Self-generated Bob session traces

All Bob session data is generated from our own hackathon Bob account and sessions. No third-party session data, client data, or private session data is used.

### 3. Public documentation references

The product incorporates documented IBM Bob rollback behavior from public IBM documentation. All referenced claims are clearly marked as DOCUMENTED_ONLY until experimentally confirmed.

### Compliance statements

- No personal data (PII) in any fixture or test file
- No client or company confidential data
- No social-media data
- No scraped or harvested data
- All data generated for and by this hackathon submission

### Data retention

Synthetic fixtures are committed to the repository for reproducibility. Generated proof artifacts (receipts, manifests, raw outputs) are committed only after being reviewed to confirm no sensitive data is present.
