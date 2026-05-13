# -*- coding: utf-8 -*-
{
    'name': 'Ministry — Annual Support Plans',
    'version': '19.0.1.0.0',
    'category': 'Ministry / Sports Support',
    'summary': 'Annual federation support plans with activity lines, KPIs, and budget linkage',
    'description': """
Ministry — Annual Support Plans
==================================
Manages annual support plans submitted by federations. Each plan links to the
federation, fiscal year, estimated budget, a list of planned activities with
support items and target KPIs, and optional Odoo analytic budget records.

Hierarchical Roles:
- Admin: Full CRUD on all annual plans.
- Manager / Department Head: Approve and review plans.
- Officers: Review submitted plans.
- Federation Portal: Own federation's plans only.
    """,
    'author': 'Kaizen Principles - AI',
    'maintainer': 'Kaizen Principles',
    'website': 'https://www.kaizenae.com',
    'depends': [
        'account',
        'account_budget',
        'analytic',
        'kaz_ai_ministry_federation',
        'kaz_ai_ministry_support_item',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/record_rules.xml',
        'data/demo_annual_plans.xml',
        'views/ministry_annual_plan_views.xml',
        'views/menus.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
