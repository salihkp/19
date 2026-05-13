# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


VIOLATION_TYPES = [
    ('financial_misuse', 'Financial Misuse'),
    ('missing_report', 'Missing Post-Event Report'),
    ('governance', 'Governance Failure'),
    ('facilities', 'Facilities Non-Compliance'),
    ('athlete_welfare', 'Athlete Welfare Breach'),
    ('other', 'Other'),
]

SEVERITY_LEVELS = [
    ('minor', 'Minor'),
    ('moderate', 'Moderate'),
    ('major', 'Major'),
    ('critical', 'Critical'),
]


class MinistryViolation(models.Model):
    _name = 'ministry.violation'
    _description = 'Inspection Violation'
    _inherit = ['mail.thread']
    _order = 'inspection_id desc, severity desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        default=lambda self: _('New'),
        help='Unique violation reference, auto-generated on creation.',
    )
    inspection_id = fields.Many2one(
        'ministry.inspection',
        string='Inspection',
        required=True,
        ondelete='cascade',
        help='The inspection during which this violation was identified.',
    )
    federation_id = fields.Many2one(
        'res.partner',
        string='Federation',
        related='inspection_id.federation_id',
        store=True,
        help='Federation associated with the parent inspection.',
    )
    violation_type = fields.Selection(
        selection=VIOLATION_TYPES,
        string='Violation Type',
        required=True,
        tracking=True,
        help='Category of the violation identified.',
    )
    severity = fields.Selection(
        selection=SEVERITY_LEVELS,
        string='Severity',
        required=True,
        default='minor',
        tracking=True,
        help='Severity level determines the urgency of follow-up action required.',
    )
    description = fields.Text(
        string='Description',
        required=True,
        help='Detailed description of the violation and its context.',
    )
    evidence_attachment_ids = fields.Many2many(
        'ir.attachment',
        'ministry_violation_evidence_rel',
        'violation_id',
        'attachment_id',
        string='Evidence',
        help='Supporting documents, images, or files evidencing the violation.',
    )
    # legal_action_ids is injected by kaz_ai_ministry_legal_affairs to avoid a
    # circular dependency. Keep a base count field so inspection views load
    # before legal affairs is installed.
    legal_action_count = fields.Integer(
        string='Legal Action Count',
        default=0,
        help='Number of legal actions linked to this violation.',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='inspection_id.company_id',
        store=True,
        help='Company context inherited from the parent inspection.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Assign sequence reference on creation."""
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('ministry.violation') or _('New')
        return super().create(vals_list)
