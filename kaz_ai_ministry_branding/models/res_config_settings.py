# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ministry_system_name_en = fields.Char(
        string='System Name (English)',
        config_parameter='ministry.system_name_en',
        default='Sports Federation Financial Support Management System',
        help='Official English name of the system displayed in reports and portal.',
    )
    ministry_system_name_ar = fields.Char(
        string='System Name (Arabic)',
        config_parameter='ministry.system_name_ar',
        default='نظام إدارة الدعم المالي للاتحادات الرياضية',
        help='Official Arabic name of the system displayed in reports and portal.',
    )
    ministry_fiscal_year = fields.Char(
        string='Current Fiscal Year',
        config_parameter='ministry.fiscal_year',
        default='2026',
        help='Active fiscal year used as default in annual plans and request filtering.',
    )
    ministry_support_email = fields.Char(
        string='Support Email',
        config_parameter='ministry.support_email',
        default='support@ministry.gov.ae',
        help='Contact email shown on portal pages and outgoing email templates.',
    )
