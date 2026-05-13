# -*- coding: utf-8 -*-
{
    'name': 'Ministry — Calculation Engine',
    'version': '19.0.1.0.0',
    'category': 'Ministry / Sports Support',
    'summary': 'Eligibility and eligible amount calculation service for support requests',
    'description': """
Ministry — Calculation Engine
================================
Pure Python service that computes eligible amounts, YoY variance, and applies
pending deductions for each support request. Hooks into ministry.support.request
via compute methods. No UI — this module is a calculation library.

Hierarchical Roles:
- Admin: Can view calculation results and logs.
- All internal roles: Benefit from computed values on support requests.
    """,
    'author': 'Kaizen Principles - AI',
    'maintainer': 'Kaizen Principles',
    'website': 'https://www.kaizenae.com',
    'depends': [
        'kaz_ai_ministry_support_item',
        'kaz_ai_ministry_annual_plan',
    ],
    'data': [
        'security/ir.model.access.csv',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
