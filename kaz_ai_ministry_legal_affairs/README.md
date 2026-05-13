# Ministry Legal Affairs

## Purpose
Legal action and sanction management for sports federations. Supports issuance of warnings, financial deductions, and suspension orders, automatically creating pending deduction queue entries for financial follow-through.

## Key Features
- Three action types: Warning Letter, Financial Deduction, Suspension
- Four-state lifecycle: Draft → Issued → Applied → Closed
- Automatic `ministry.pending.deduction` creation on Apply for deduction-type actions
- Links to triggering inspection and specific violation
- Extends `ministry.violation` with legal action count and navigation (injected without circular dependency)
- Demo: 1 warning + 1 deduction (AED 10,000) against Athletics Federation

## Dependencies
- `kaz_ai_ministry_inspection`
- `kaz_ai_ministry_support_request`
- `kaz_ai_ministry_branding`

## Installation
```
docker exec -it odoo_19_ai odoo -d <db> -i kaz_ai_ministry_legal_affairs --no-http
```

## Access Roles
- Manager: Full CRUD
- Legal Officer: Read, write, and create records; no delete
- Department Head: Read and write
- Analyst: Read only
- Technical Officer: Read only
