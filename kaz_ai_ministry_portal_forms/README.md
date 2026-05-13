# Ministry Portal Forms

## Purpose
Federation self-service portal for championship participation/hosting applications and post-event reports. Federations interact through the Odoo website portal; Ministry staff review and act through the backend.

## Key Features
- **Participation Applications**: 15-day pre-event deadline, 6 championship levels (Local → Olympic)
- **Hosting Applications**: 30-day pre-event deadline, venue capacity and country tracking
- **Post-Event Reports**: 15-day post-event deadline, late detection flag, achievement % for risk scoring
- Portal record isolation: each federation user sees only their own records
- Backend review workflows with group-restricted action buttons
- Automatic support request closure when an accepted report links to an `awaiting_report` SR
- Demo: 6 participations, 2 hostings, 5 post-event reports across all 3 federations

## Portal Routes
- `/my/federation/dashboard`: Federation dashboard
- `/my/championships/participation`: List applications
- `/my/championships/participation/new`: Submit new application
- `/my/championships/hosting`: List hosting applications
- `/my/championships/hosting/new`: Submit hosting application
- `/my/championships/post-event-report`: List reports
- `/my/championships/post-event-report/new`: Submit report
- `/my/championships/downloads`: Download official Ministry forms, reports, and reference documents
- `/ministry/reports/financial-support/entities-clubs.xlsx`: Generate financial support XLSX from system data

## Dependencies
- `kaz_ai_ministry_support_request`
- `kaz_ai_ministry_branding`
- `portal`
- `web`

## Installation
```
docker exec -it odoo_19_ai odoo i18n loadlang -d <db> -l ar_001
docker exec -it odoo_19_ai odoo -d <db> -i kaz_ai_ministry_portal_forms --no-http
```

## Access Roles
- Manager: Full CRUD in the backend
- Technical Officer: Read and write for backend review
- Portal User: Create and read own federation records
