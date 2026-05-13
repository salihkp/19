# -*- coding: utf-8 -*-
{
    'name': 'Ministry Inspection',
    'version': '19.0.1.0.0',
    'summary': 'Field inspections and violation tracking for sports federations',
    'category': 'Ministry / Sports Support',
    'author': 'KAZ-AI',
    'website': 'https://kaizenae.com',
    'license': 'OPL-1',
    'depends': [
        'kaz_ai_ministry_federation',
        'kaz_ai_ministry_branding',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/record_rules.xml',
        'data/sequences.xml',
        'views/ministry_inspection_views.xml',
        'views/ministry_violation_views.xml',
        'views/menus.xml',
        'data/demo_inspections.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
