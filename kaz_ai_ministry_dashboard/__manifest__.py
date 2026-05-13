# -*- coding: utf-8 -*-
{
    "name": "Ministry Dashboard",
    "version": "19.0.1.0.0",
    "summary": "Executive dashboard for sports federation financial support",
    "category": "Ministry / Sports Support",
    "author": "Kaizen Principles",
    "website": "https://www.kaizenae.com",
    "license": "LGPL-3",
    "depends": [
        "web",
        "mail",
        "kaz_ai_ministry_analytics",
        "kaz_ai_ministry_support_request",
        "kaz_ai_ministry_branding",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/dashboard_views.xml",
        "views/menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "kaz_ai_ministry_dashboard/static/src/components/kaz_ai_ministry_dashboard.js",
            "kaz_ai_ministry_dashboard/static/src/components/kaz_ai_ministry_dashboard.xml",
            "kaz_ai_ministry_dashboard/static/src/scss/kaz_ai_ministry_dashboard.scss",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}

