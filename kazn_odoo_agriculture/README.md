# Kaizen Agriculture / Farm Management

Plan and execute crop seasons per farm location with full resource tracking, project automation, and multi-company support.

## Key Features

- Cropping Requests with states: New -> Confirmed -> In Progress -> Done
- One-click project creation and task cloning when a request starts
- Crop Process Templates with equipment, fleet, and animal requirements
- Materials, Labour, and Overheads planning per crop (products / UoM / qty)
- Incident logging and disease cure library with auto-fill
- Multi-company security, dashboards, and PDF reports

## Dependencies

- `project`
- `stock`
- `website_customer`
- `maintenance`
- `fleet`

## Installation

```bash
docker exec -it <container> odoo -i kazn_odoo_agriculture -d <db_name> --no-http --stop-after-init
```

## Access Roles

| Role | Permissions |
|---|---|
| Agriculture User | Read / Write / Create own Crop Requests |
| Agriculture Manager | Full access to all Crop Requests and configuration |

## Configuration

No post-install steps required. Fleet, Maintenance, and Project apps must be installed before installing this module.

## Changelog

### 19.0.1.1.1 - 2026-04-18

- [FIX] `action_schedule_reminders()` now uses `res_model_id` (Odoo 19 compatible) to avoid `mail_activity_check_res_id_is_set_if_model` SQL errors.
- [FIX] Reminder creation now avoids duplicate mail activities for the same request/date/summary.
- [FIX] Prevent duplicate project creation from `action_in_progress()` when a project is already linked.
- [FIX] Corrected `project.project` crop request counter logic to compute per record.
- [FIX] Improved M2M assignment command for copied task equipment lines.
- [FIX] Cleaned manifest/README text encoding and metadata formatting.

### 19.0.1.1.0 - 2026-04-16

- [FIX] Missing `# -*- coding: utf-8 -*-` encoding declaration on all Python files.
- [FIX] `create()` method: `return super()` was inside the `for` loop; sequence number only assigned to first record in a batch.
- [FIX] `action_in_progress()` hardcoded `alias_id` removed; method cleanup.
- [FIX] Counter compute methods corrected to avoid cross-record leakage.
- [FIX] Deprecated chatter markup migrated to `<chatter/>`.
- [FIX] Invalid `required=True` removed from unsupported relational field definitions.
- [FIX] Record rules adjusted to avoid global/group conflict.
- [FIX] Sequence prefix normalized to `CROP/REQ/` with `padding=5`.
- [UPDT] Added `company_id` to core models for multi-company support.
