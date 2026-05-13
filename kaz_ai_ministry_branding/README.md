# Ministry of Sports — Branding & Identity

**Module:** `kaz_ai_ministry_branding`
**Version:** 19.0.1.0.0

## Purpose
Provides the foundational identity layer for the Sports Federation Financial Support Management System: Ministry of Sports color palette, login screen branding, PDF report header/footer, security group definitions, system parameters, and demo user accounts.

## Key Features
- Ministry gold/black/red color palette applied backend-wide via SCSS
- Branded login screen with Ministry logo, EN + AR system name, UAE flag colors
- PDF report header and footer templates with Ministry gold band
- 8 security groups covering all operational roles
- 6 ministry staff demo users + system configuration parameters

## Dependencies
- `base`, `web`, `mail`, `portal`, `base_setup`

## Installation
```bash
docker exec -it odoo_19_ai odoo i18n loadlang -d ministry_support -l ar_001
docker exec -it odoo_19_ai odoo -i kaz_ai_ministry_branding -d ministry_support --no-http --stop-after-init
```

## Access Roles
| Group | Access |
|---|---|
| Admin | Full system access |
| Manager | Implies all officer groups |
| Officer (Technical/Financial) | Assigned requests and reviews |
| Department Head | Final approvals |
| Inspector | Inspection and violation records |
| Legal Officer | Legal actions and deduction queue |
| Analyst | Read-only analytics and dashboards |
| Federation Portal | Own federation data only (portal) |

## Configuration
After install, navigate to **Settings → Technical → Parameters → System Parameters** to adjust:
- `ministry.system_name_en` / `ministry.system_name_ar`
- `ministry.fiscal_year`
- `ministry.annual_budget`
- Risk scoring weight parameters
