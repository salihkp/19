# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class MinistryViolationLegalExt(models.Model):
    """Extends ministry.violation with legal action fields.

    Defined here (not in kaz_ai_ministry_inspection) to avoid a circular
    dependency: inspection ← legal_affairs ← inspection.
    """
    _inherit = 'ministry.violation'

    legal_action_ids = fields.One2many(
        'ministry.legal.action',
        'violation_id',
        string='Legal Actions',
        help='Legal actions initiated as a result of this violation.',
    )
    legal_action_count = fields.Integer(
        string='Legal Action Count',
        compute='_compute_legal_action_count',
        help='Number of legal actions linked to this violation.',
    )

    @api.depends('legal_action_ids')
    def _compute_legal_action_count(self):
        for rec in self:
            rec.legal_action_count = len(rec.legal_action_ids)

    def action_open_legal_actions(self):
        """Open related legal actions."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Legal Actions — %s') % self.name,
            'res_model': 'ministry.legal.action',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [('violation_id', '=', self.id)],
            'context': {
                'default_violation_id': self.id,
                'default_federation_id': self.federation_id.id,
            },
        }
