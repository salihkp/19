# -*- coding: utf-8 -*-
{
    'name': 'Ministry Portal Forms',
    'version': '19.0.1.1.0',
    'summary': 'Federation self-service portal: championship applications and post-event reports',
    'category': 'Ministry / Sports Support',
    'author': 'KAZ-AI',
    'website': 'https://kaizenae.com',
    'license': 'OPL-1',
    'depends': [
        'kaz_ai_ministry_support_request',
        'kaz_ai_ministry_branding',
        'portal',
        'web',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/record_rules.xml',
        'data/sequences.xml',
        'reports/portal_form_reports.xml',
        'views/portal_templates.xml',
        'views/backend_views.xml',
        'views/menus.xml',
        'data/demo_portal_data.xml',
        'data/demo_portal_budget_lines.xml',
    ],
    'demo': [],
    'assets': {
        'web.report_assets_common': [
            'kaz_ai_ministry_portal_forms/static/src/css/ministry_report_fonts.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
