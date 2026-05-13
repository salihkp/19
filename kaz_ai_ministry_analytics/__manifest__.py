# -*- coding: utf-8 -*-
{
    'name': 'Ministry Analytics',
    'version': '19.0.1.0.0',
    'summary': 'Budget analytics, anomaly detection, and forecasting for sports federation support',
    'category': 'Ministry / Sports Support',
    'author': 'KAZ-AI',
    'website': 'https://kaizenae.com',
    'license': 'OPL-1',
    'depends': [
        'kaz_ai_ministry_support_request',
        'kaz_ai_ministry_risk_scoring',
        'kaz_ai_ministry_branding',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/ministry_analytics_alert_views.xml',
        'views/menus.xml',
        'data/scheduled_actions.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
