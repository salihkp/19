# -*- coding: utf-8 -*-
from odoo import fields, models


class MinistryPendingDeduction(models.Model):
    _inherit = 'ministry.pending.deduction'

    legal_action_id = fields.Many2one(
        'ministry.legal.action',
        string='Legal Action',
        help='The legal action that created this deduction.',
    )
