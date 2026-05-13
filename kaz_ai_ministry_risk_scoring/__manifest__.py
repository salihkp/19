# -*- coding: utf-8 -*-
{
    'name': 'Ministry — Risk Scoring Engine',
    'version': '19.0.1.0.0',
    'category': 'Ministry / Sports Support',
    'summary': 'Multi-dimensional risk scoring for federations and support requests',
    'description': """
Ministry — Risk Scoring Engine
==================================
Computes a composite risk score (0–100) and risk level (low/medium/high) for
each federation and support request using five weighted dimensions:
budget depletion, YoY variance, federation violation history, missing reports,
and performance achievement. Weights are configurable via system parameters.

Hierarchical Roles:
- Admin / Manager: Access to risk configuration and override.
- All internal roles: View risk badges on federation and request records.
    """,
    'author': 'Kaizen Principles - AI',
    'maintainer': 'Kaizen Principles',
    'website': 'https://www.kaizenae.com',
    'depends': [
        'kaz_ai_ministry_calc_engine',
    ],
    'data': [
        'security/ir.model.access.csv',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
