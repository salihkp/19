# -*- coding: utf-8 -*-
from odoo import fields, models


class MinistryPendingDeduction(models.Model):
    """Queue of financial deductions to be applied on the next payment.

    Records are created by ministry.legal.action when action_type = 'deduction'.
    Consumed FIFO by MinistryCalcEngine.apply_pending_deductions().
    """
    _name = 'ministry.pending.deduction'
    _description = 'Pending Deduction'
    _inherit = ['mail.thread']
    _order = 'create_date asc'

    federation_id = fields.Many2one(
        'res.partner',
        string='Federation',
        required=True,
        domain="[('is_federation', '=', True)]",
        tracking=True,
        help='The federation this deduction will be charged against.',
    )
    deduction_amount = fields.Float(
        string='Deduction Amount (AED)',
        required=True,
        digits=(16, 2),
        tracking=True,
        help='AED amount to deduct from the next approved payment.',
    )
    reason = fields.Char(
        string='Reason',
        help='Brief description of why this deduction was issued.',
    )
    state = fields.Selection(
        [('pending', 'Pending'), ('applied', 'Applied'), ('cancelled', 'Cancelled')],
        string='Status',
        default='pending',
        tracking=True,
        help='Pending: queued. Applied: consumed on a payment. Cancelled: voided.',
    )
    applied_on_request_id = fields.Many2one(
        'ministry.support.request',
        string='Applied On Request',
        readonly=True,
        help='The support request payment this deduction was applied against.',
    )
    applied_date = fields.Date(string='Applied Date', readonly=True)
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
    )
