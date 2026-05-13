# Ministry Inspection

## Purpose
Field inspection management for sports federations. Enables Ministry inspectors to schedule, conduct, and record compliance visits, capturing findings, performance evaluations, and violation records.

## Key Features
- Three visit types: Scheduled, Surprise, Follow-Up
- Calendar view for inspection scheduling
- Per-inspection violation log with severity rating (Minor → Critical)
- Photo evidence attachment support
- Performance evaluation: Excellent / Good / Acceptable / Poor
- Chatter tracking for all state transitions
- Demo: 4 inspections (3 Done, 1 In Progress) with 2 violations on Athletics Federation

## Dependencies
- `kaz_ai_ministry_federation`
- `kaz_ai_ministry_branding`
- `mail`

## Installation
```
docker exec -it odoo_19_ai odoo -d <db> -i kaz_ai_ministry_inspection --no-http
```

## Access Roles
- Manager: Full CRUD
- Inspector: Read, write, and create own assignments
- Technical Officer: Read only
- Analyst: Read only
