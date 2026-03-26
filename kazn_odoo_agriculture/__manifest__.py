{
    "name": "Kaizen Agriculture / Farm Management",
    "version": "19.0.1.0.1",
    "summary": "Plan crop seasons, standardize field processes, allocate resources, and launch projects in one click.",
    "description": """
    Kaizen Agriculture / Farm Management
    Plan and execute crop seasons per farm location:
    • Cropping Requests with states (New → Confirmed → In Progress → Done).
    • 1‑click project creation and task cloning when a request starts.
    • Crop Process Templates with equipment, fleet, and animal requirements.
    • Materials, Labor, and Overheads planning per crop (products/UoM/qty).
    • Incidents logging and disease cures library with auto-fill.
    • Multi-company security, dashboards, and PDF reports.
    Integrated Odoo apps: Projects, Stock, Maintenance, Fleet, Website (customer map).
    """,
    "author": "Kaizen Principles",
    "website": "http://www.kaizenae.com/",
    'price': 147.0,
    'currency': 'USD',
    'license': 'OPL-1',
    'images': ['static/description/banner.gif'],
    'depends': ['project','stock','website_customer','maintenance','fleet'],
    'data':[
        'security/agriculture_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'report/farmer_cropping_request_report.xml',
        'report/farmer_location_crops_report.xml',
        'views/res_partner_view.xml',
        'views/crops_view.xml',
        'views/crops_material_job_view.xml',
        'views/crops_dieases_view.xml',
        'views/project_task_view.xml',
        'views/crops_animals_view.xml',
        'views/google_map_template_view.xml',
        'views/crops_fleet_view.xml',
        'views/crops_incident_view.xml',
        'views/crops_tasks_template_view.xml',
        'views/farmer_cropping_request_view.xml',
        'views/menu_item.xml'
        ],
    'installable' : True,
}
