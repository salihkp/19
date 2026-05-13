# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MinistryInspection(models.Model):
    _name = 'ministry.inspection'
    _description = 'Federation Field Inspection'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'visit_date desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        default=lambda self: _('New'),
        help='Unique inspection reference, auto-generated on creation.',
    )
    federation_id = fields.Many2one(
        'res.partner',
        string='Federation',
        required=True,
        domain=[('is_federation', '=', True)],
        tracking=True,
        help='The federation being inspected.',
    )
    visit_date = fields.Date(
        string='Visit Date',
        required=True,
        tracking=True,
        help='Scheduled or actual date of the inspection visit.',
    )
    visit_type = fields.Selection(
        selection=[
            ('scheduled', 'Scheduled'),
            ('surprise', 'Surprise'),
            ('follow_up', 'Follow-Up'),
        ],
        string='Visit Type',
        required=True,
        default='scheduled',
        tracking=True,
        help='Nature of the inspection visit.',
    )
    inspector_ids = fields.Many2many(
        'res.users',
        'ministry_inspection_inspector_rel',
        'inspection_id',
        'user_id',
        string='Inspectors',
        domain=[('share', '=', False)],
        help='Ministry staff assigned to conduct this inspection.',
    )
    notes = fields.Html(
        string='Inspection Notes',
        help='Detailed findings and observations during the inspection.',
    )
    photo_ids = fields.Many2many(
        'ir.attachment',
        'ministry_inspection_photo_rel',
        'inspection_id',
        'attachment_id',
        string='Photos',
        domain=[('mimetype', 'like', 'image/')],
        help='Photographic evidence captured during the inspection.',
    )
    performance_evaluation = fields.Selection(
        selection=[
            ('excellent', 'Excellent'),
            ('good', 'Good'),
            ('acceptable', 'Acceptable'),
            ('poor', 'Poor'),
        ],
        string='Performance Evaluation',
        tracking=True,
        help='Overall assessment of the federation\'s performance and compliance.',
    )
    violation_ids = fields.One2many(
        'ministry.violation',
        'inspection_id',
        string='Violations',
        help='Violations identified during this inspection.',
    )
    violation_count = fields.Integer(
        string='Violation Count',
        compute='_compute_violation_count',
        help='Total number of violations recorded for this inspection.',
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('in_progress', 'In Progress'),
            ('done', 'Done'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
        help='Current lifecycle state of the inspection.',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
        help='Company this inspection belongs to.',
    )

    @api.depends('violation_ids')
    def _compute_violation_count(self):
        for rec in self:
            rec.violation_count = len(rec.violation_ids)

    @api.model_create_multi
    def create(self, vals_list):
        """Assign sequence on creation."""
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('ministry.inspection') or _('New')
        return super().create(vals_list)

    def action_start(self):
        """Move inspection to In Progress state."""
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft inspections can be started.'))
            rec.state = 'in_progress'
            rec.message_post(body=_('Inspection started.'))

    def action_done(self):
        """Mark the inspection as completed."""
        for rec in self:
            if rec.state != 'in_progress':
                raise UserError(_('Only in-progress inspections can be marked done.'))
            if not rec.performance_evaluation:
                raise UserError(_('Please set a performance evaluation before closing the inspection.'))
            rec.state = 'done'
            rec.message_post(
                body=_(
                    'Inspection completed. Performance: %(eval)s. Violations recorded: %(count)s.',
                    eval=dict(rec._fields['performance_evaluation'].selection).get(rec.performance_evaluation),
                    count=rec.violation_count,
                )
            )

    def action_reset_draft(self):
        """Reset inspection to draft for corrections."""
        for rec in self:
            if rec.state == 'draft':
                raise UserError(_('This inspection is already in draft.'))
            rec.state = 'draft'
            rec.message_post(body=_('Inspection reset to draft.'))

    def action_open_violations(self):
        """Open related violations in a list view."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Violations — %s') % self.name,
            'res_model': 'ministry.violation',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [('inspection_id', '=', self.id)],
            'context': {'default_inspection_id': self.id, 'default_federation_id': self.federation_id.id},
        }
