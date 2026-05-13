# -*- coding: utf-8 -*-
{
    'name': 'Ministry — Federation Master Data',
    'version': '19.0.1.0.0',
    'category': 'Ministry / Sports Support',
    'summary': 'Sports federations, clubs, and sport catalog master data',
    'description': """
Ministry — Federation Master Data
====================================
Manages the federation registry: sports catalog, affiliated clubs, and
federation partner profiles with Olympic classification, player counts,
status, and risk indicators.

Hierarchical Roles:
- Admin: Full CRUD on federations, sports, clubs, and portal user assignment.
- Manager / Officers: Read and update federation profiles.
- Federation Portal: Own federation profile only (read-only).
    """,
    'author': 'Kaizen Principles - AI',
    'maintainer': 'Kaizen Principles',
    'website': 'https://www.kaizenae.com',
    'depends': [
        'base',
        'mail',
        'portal',
        'contacts',
        'kaz_ai_ministry_branding',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/record_rules.xml',
        'data/demo_sports.xml',
        'data/demo_federations.xml',
        'data/demo_users_portal.xml',
        'views/ministry_sport_views.xml',
        'views/ministry_club_views.xml',
        'views/ministry_federation_views.xml',
        'views/menus.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
