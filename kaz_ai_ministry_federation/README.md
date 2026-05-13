# Ministry — Federation Master Data

**Module:** `kaz_ai_ministry_federation`
**Version:** 19.0.1.0.0

## Purpose
Manages sports federation master data: sport catalog, affiliated clubs, and extended partner profiles with Olympic classification, player statistics, status tracking, and risk indicators.

## Key Features
- 12 sports with Olympic classification flags
- 3 demo federations: Football (Olympic/team), Athletics (Olympic/individual), Chess (non-Olympic/individual)
- 15 demo clubs (5 per federation)
- Federation kanban with risk-color coding and status badges
- Smart buttons for Requests, Inspections, and Clubs on federation form
- 6 portal demo users (2 per federation) with isolation record rules

## Dependencies
- `base`, `mail`, `portal`, `contacts`, `kaz_ai_ministry_branding`

## Installation
```bash
docker exec -it odoo_19_ai odoo -i kaz_ai_ministry_federation -d ministry_support --no-http --stop-after-init
```

## Access Roles
| Role | Access |
|---|---|
| Admin / Manager | Full CRUD on federations, sports, clubs |
| Officers | Read federation profiles |
| Federation Portal | Own federation record only (read-only) |
