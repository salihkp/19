# -*- coding: utf-8 -*-
{
    'name': 'Ministry Legal Affairs',
    'version': '19.0.1.0.0',
    'summary': 'Legal actions, sanctions, and deduction management for sports federations',
    'category': 'Ministry / Sports Support',
    'author': 'KAZ-AI',
    'website': 'https://kaizenae.com',
    'license': 'OPL-1',
    'depends': [
        'kaz_ai_ministry_inspection',
        'kaz_ai_ministry_support_request',
        'kaz_ai_ministry_branding',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/record_rules.xml',
        'data/sequences.xml',
        'views/ministry_legal_action_views.xml',
        'views/ministry_violation_ext_views.xml',
        'views/menus.xml',
        'data/demo_legal_actions.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
