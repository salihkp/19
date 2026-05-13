# -*- coding: utf-8 -*-
from odoo import fields, models


class MinistryAttachmentType(models.Model):
    _name = 'ministry.attachment.type'
    _description = 'Required Attachment Type'
    _order = 'name'

    name = fields.Char(string='Attachment Type', required=True,
        help='Label shown to the federation user when uploading (e.g., Official Invitation, Budget Breakdown).')
    code = fields.Char(string='Code', size=20,
        help='Short code used in validation logic.')
    is_mandatory = fields.Boolean(string='Mandatory', default=True,
        help='If checked, the request cannot be submitted without this attachment.')
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
    )
