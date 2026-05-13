# -*- coding: utf-8 -*-
from odoo import fields, models


class MinistryAnalyticsAlert(models.Model):
    _name = 'ministry.analytics.alert'
    _description = 'Ministry Analytics Alert'
    _order = 'create_date desc'

    name = fields.Char(
        string='Alert',
        required=True,
        help='Short description of the detected anomaly or alert condition.',
    )
    alert_type = fields.Selection(
        selection=[
            ('abnormal_increase', 'Abnormal Budget Increase'),
            ('high_burn_rate', 'High Budget Burn Rate'),
            ('forecast_overrun', 'Forecast Overrun'),
            ('missing_report', 'Missing Post-Event Reports'),
            ('risk_threshold', 'Risk Threshold Breach'),
        ],
        string='Alert Type',
        required=True,
        help='Category of the analytics alert.',
    )
    severity = fields.Selection(
        selection=[
            ('info', 'Information'),
            ('warning', 'Warning'),
            ('critical', 'Critical'),
        ],
        string='Severity',
        required=True,
        default='warning',
        help='Urgency level of this alert.',
    )
    federation_id = fields.Many2one(
        'res.partner',
        string='Federation',
        domain=[('is_federation', '=', True)],
        help='Federation affected by this alert, if specific.',
    )
    detail = fields.Text(
        string='Detail',
        help='Additional context and data points supporting the alert.',
    )
    is_acknowledged = fields.Boolean(
        string='Acknowledged',
        default=False,
        help='Mark as acknowledged once reviewed by an analyst.',
    )
    acknowledged_by = fields.Many2one(
        'res.users',
        string='Acknowledged By',
        readonly=True,
        help='User who acknowledged this alert.',
    )
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True,
    )

    def action_acknowledge(self):
        """Mark the alert as acknowledged."""
        for rec in self:
            if rec.is_acknowledged:
                continue
            rec.is_acknowledged = True
            rec.acknowledged_by = self.env.user.id
