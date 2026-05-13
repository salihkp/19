# -*- coding: utf-8 -*-
{
    'name': 'Ministry — Support Item Catalog',
    'version': '19.0.1.0.0',
    'category': 'Ministry / Sports Support',
    'summary': 'Support item catalog with calculation rules for all four support categories',
    'description': """
Ministry — Support Item Catalog
==================================
Defines the full catalog of financial support items across all four categories:
Operational, Technical, General Financial, and Activity Support.
Each item carries a calculation method (fixed amount, per-count, or per-request),
maximum limit, eligibility expression, and required attachment types.

Hierarchical Roles:
- Admin: Full CRUD on support groups, items, and attachment types.
- Manager / Officers: Read-only access to the catalog.
- Federation Portal: Read-only access to items applicable to their requests.
    """,
    'author': 'Kaizen Principles - AI',
    'maintainer': 'Kaizen Principles',
    'website': 'https://www.kaizenae.com',
    'depends': [
        'account',
        'analytic',
        'kaz_ai_ministry_branding',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/demo_support_groups.xml',
        'data/demo_support_items.xml',
        'views/ministry_support_item_views.xml',
        'views/menus.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
