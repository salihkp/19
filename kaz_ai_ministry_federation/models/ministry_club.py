# -*- coding: utf-8 -*-
from odoo import fields, models


class MinistryClub(models.Model):
    _name = 'ministry.club'
    _description = 'Affiliated Club'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'federation_id, name'

    name = fields.Char(
        string='Club Name',
        required=True,
        tracking=True,
        help='Full official name of the affiliated club.',
    )
    federation_id = fields.Many2one(
        'res.partner',
        string='Federation',
        domain="[('is_federation', '=', True)]",
        required=True,
        tracking=True,
        help='The parent federation this club is affiliated with.',
    )
    city = fields.Char(
        string='City',
        help='City where the club is based.',
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Uncheck to archive this club without deleting it.',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
