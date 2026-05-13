# -*- coding: utf-8 -*-
{
    'name': 'Ministry of Sports - Branding & Identity',
    'version': '19.0.1.0.0',
    'category': 'Ministry / Sports Support',
    'summary': 'Ministry of Sports branding, security groups, and system identity',
    'description': """
Ministry of Sports - Branding & Identity
=========================================
Provides the foundational identity layer for the Sports Federation Financial
Support Management System: color palette, login screen, PDF report headers,
security group definitions, and system parameters.

Hierarchical Roles:
- Admin: Full access to all records, configuration, and settings.
- Manager: Access to all support operations and reporting.
- Officer (Technical/Financial): Access to assigned requests and reviews.
- Inspector: Access to inspection and violation records.
- Legal Officer: Access to legal actions and deduction queues.
- Analyst: Read-only access to analytics and dashboards.
- Federation Portal: Isolated access to own federation data only.
    """,
    'author': 'Kaizen Principles - AI',
    'maintainer': 'Kaizen Principles',
    'website': 'https://www.kaizenae.com',
    'depends': [
        'base',
        'web',
        'mail',
        'portal',
        'base_setup',
    ],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'data/languages.xml',
        'data/system_params.xml',
        'data/demo_users.xml',
        'views/login_templates.xml',
        'report/report_layout.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'kaz_ai_ministry_branding/static/src/scss/ministry_branding.scss',
        ],
        'web.assets_frontend': [
            'kaz_ai_ministry_branding/static/src/scss/ministry_login.scss',
            'kaz_ai_ministry_branding/static/src/scss/ministry_portal.scss',
        ],
        'web.login_assets': [
            'kaz_ai_ministry_branding/static/src/scss/ministry_login.scss',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
}
