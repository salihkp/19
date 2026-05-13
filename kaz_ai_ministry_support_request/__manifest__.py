# -*- coding: utf-8 -*-
{
    'name': 'Ministry — Support Request Lifecycle',
    'version': '19.0.1.0.0',
    'category': 'Ministry / Sports Support',
    'summary': 'Complete support request lifecycle from draft to closed, with approvals and payments',
    'description': """
Ministry — Support Request Lifecycle
=======================================
Core module managing the full financial support request lifecycle:
draft → submitted → under review → approved → to pay → paid → awaiting report → closed.
Integrates with Odoo Approvals (multi-level), Accounting (vendor bill auto-creation),
and the Ministry calculation and risk scoring engines.

Hierarchical Roles:
- Admin: Full CRUD and all state transitions.
- Department Head: Final approval on high-value and international requests.
- Officer (Technical/Financial): Review and recommend at each level.
- Federation Portal: Own federation's requests only.
    """,
    'author': 'Kaizen Principles - AI',
    'maintainer': 'Kaizen Principles',
    'website': 'https://www.kaizenae.com',
    'depends': [
        'account',
        'analytic',
        'mail',
        'kaz_ai_ministry_risk_scoring',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/record_rules.xml',
        'data/sequences.xml',
        'data/analytic_plans.xml',
        'data/demo_requests.xml',
        'views/ministry_support_request_views.xml',
        'views/menus.xml',
        'report/support_request_report.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
