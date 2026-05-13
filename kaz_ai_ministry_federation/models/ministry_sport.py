# -*- coding: utf-8 -*-
from odoo import fields, models


class MinistrySport(models.Model):
    _name = 'ministry.sport'
    _description = 'Sport'
    _inherit = ['mail.thread']
    _rec_name = 'name'
    _order = 'name'

    name = fields.Char(
        string='Sport Name',
        required=True,
        tracking=True,
        help='Official name of the sport (e.g., Football, Athletics, Chess).',
    )
    code = fields.Char(
        string='Code',
        size=10,
        help='Short code used in reports and sequence references (e.g., FOOT, ATH).',
    )
    is_olympic = fields.Boolean(
        string='Olympic Sport',
        tracking=True,
        help='Indicates whether this sport is part of the Olympic programme.',
    )
    federation_count = fields.Integer(
        string='Federations',
        compute='_compute_federation_count',
        help='Number of active federations registered under this sport.',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )

    def _compute_federation_count(self):
        """Compute the number of active federations linked to this sport."""
        for sport in self:
            sport.federation_count = self.env['res.partner'].search_count([
                ('is_federation', '=', True),
                ('sport_id', '=', sport.id),
                ('federation_status', '=', 'active'),
            ])
