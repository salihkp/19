# -*- coding: utf-8 -*-
from odoo import fields, models


class MinistrySupportGroup(models.Model):
    _name = 'ministry.support.group'
    _description = 'Support Group'
    _order = 'sequence, name'

    name = fields.Char(string='Group Name', required=True)
    sequence = fields.Integer(default=10)
    category = fields.Selection(
        [
            ('operational', 'Operational Support'),
            ('technical', 'Technical Support'),
            ('general', 'General Financial Support'),
            ('activity', 'Activity Support'),
        ],
        string='Category',
        required=True,
        help='The support category this group belongs to.',
    )
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
    )
