# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class MinistryLegalAction(models.Model):
    _name = 'ministry.legal.action'
    _description = 'Federation Legal Action'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'issue_date desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        default=lambda self: _('New'),
        help='Unique legal action reference, auto-generated on creation.',
    )
    federation_id = fields.Many2one(
        'res.partner',
        string='Federation',
        required=True,
        domain=[('is_federation', '=', True)],
        tracking=True,
        help='The federation against which this action is issued.',
    )
    inspection_id = fields.Many2one(
        'ministry.inspection',
        string='Related Inspection',
        domain="[('federation_id', '=', federation_id)]",
        help='Inspection that triggered this legal action, if applicable.',
    )
    violation_id = fields.Many2one(
        'ministry.violation',
        string='Related Violation',
        domain="[('inspection_id', '=', inspection_id)]",
        help='Specific violation that prompted this action.',
    )
    action_type = fields.Selection(
        selection=[
            ('warning', 'Warning Letter'),
            ('deduction', 'Financial Deduction'),
            ('suspension', 'Suspension'),
        ],
        string='Action Type',
        required=True,
        tracking=True,
        help='Type of legal or administrative action being taken.',
    )
    deduction_amount = fields.Monetary(
        string='Deduction Amount (AED)',
        currency_field='currency_id',
        help='Amount to be deducted from future support payments. Required when action type is Deduction.',
    )
    deduction_reason = fields.Char(
        string='Deduction Reason',
        help='Short reason for the financial deduction, recorded on the pending deduction.',
    )
    issue_date = fields.Date(
        string='Issue Date',
        default=fields.Date.context_today,
        required=True,
        help='Date on which this action was officially issued.',
    )
    effective_date = fields.Date(
        string='Effective Date',
        help='Date from which the action takes effect (e.g., suspension start date).',
    )
    decision_text = fields.Html(
        string='Decision Text',
        help='Full text of the legal decision, warning notice, or suspension order.',
    )
    issued_by = fields.Many2one(
        'res.users',
        string='Issued By',
        default=lambda self: self.env.user,
        readonly=True,
        help='Ministry officer who issued this action.',
    )
    pending_deduction_id = fields.Many2one(
        'ministry.pending.deduction',
        string='Pending Deduction',
        readonly=True,
        copy=False,
        help='Pending deduction record created when this action is applied.',
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('issued', 'Issued'),
            ('applied', 'Applied'),
            ('closed', 'Closed'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
        help='Lifecycle state of the legal action.',
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        help='Currency for the deduction amount.',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
        help='Company context for this legal action.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Assign sequence on creation."""
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('ministry.legal.action') or _('New')
        return super().create(vals_list)

    @api.constrains('action_type', 'deduction_amount')
    def _check_deduction_amount(self):
        """Ensure deduction type has a positive amount."""
        for rec in self:
            if rec.action_type == 'deduction' and rec.deduction_amount <= 0:
                raise ValidationError(_('A financial deduction action must have a positive deduction amount.'))

    def action_issue(self):
        """Formally issue the legal action — moves to Issued state."""
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft actions can be issued.'))
            rec.state = 'issued'
            rec.message_post(
                body=_(
                    'Legal action %(name)s issued against %(fed)s. Type: %(type)s.',
                    name=rec.name,
                    fed=rec.federation_id.name,
                    type=dict(rec._fields['action_type'].selection).get(rec.action_type),
                )
            )

    def action_apply(self):
        """Apply the action — creates a pending deduction if type is deduction."""
        for rec in self:
            if rec.state != 'issued':
                raise UserError(_('Only issued actions can be applied.'))
            extra = ''
            if rec.action_type == 'deduction':
                rec._create_pending_deduction()
                extra = _('A pending deduction of %(amount)s AED has been queued.',
                          amount=f'{rec.deduction_amount:,.2f}')
            elif rec.action_type == 'suspension':
                rec._apply_federation_suspension()
                extra = _('The federation has been marked as Suspended.')
            elif rec.action_type == 'warning':
                extra = _('The warning has been recorded.')
            rec.state = 'applied'
            rec.message_post(
                body=_(
                    'Legal action %(name)s applied. %(extra)s',
                    name=rec.name,
                    extra=extra,
                )
            )

    def action_close(self):
        """Close the action once all consequences are resolved."""
        for rec in self:
            if rec.state not in ('issued', 'applied'):
                raise UserError(_('Only issued or applied actions can be closed.'))
            should_lift_suspension = rec.action_type == 'suspension' and rec.state == 'applied'
            rec.state = 'closed'
            if should_lift_suspension:
                rec._lift_federation_suspension_if_resolved()
            rec.message_post(body=_('Legal action %(name)s closed.', name=rec.name))

    def action_reset_draft(self):
        """Reset to draft for correction (only if not yet applied)."""
        for rec in self:
            if rec.state != 'issued':
                raise UserError(_('Only issued actions can be reset to draft.'))
            rec.state = 'draft'

    def action_view_pending_deduction(self):
        """Open the related pending deduction record."""
        self.ensure_one()
        if not self.pending_deduction_id:
            return {}
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pending Deduction'),
            'res_model': 'ministry.pending.deduction',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'res_id': self.pending_deduction_id.id,
        }

    def _create_pending_deduction(self):
        """Create a ministry.pending.deduction record from this legal action.

        Workflow:
            1. Build reason string from action reference and deduction_reason.
            2. Create the pending deduction linked to this action.
            3. Link the created record back via pending_deduction_id.
        """
        self.ensure_one()
        reason = self.deduction_reason or _(
            'Deduction per legal action %(name)s', name=self.name
        )
        deduction = self.env['ministry.pending.deduction'].create({
            'federation_id': self.federation_id.id,
            'deduction_amount': self.deduction_amount,
            'reason': reason,
            'legal_action_id': self.id,
            'state': 'pending',
            'company_id': self.company_id.id,
        })
        self.pending_deduction_id = deduction.id

    def _apply_federation_suspension(self):
        """Mark the linked federation as suspended when a suspension applies."""
        self.ensure_one()
        reason = _(
            'Legal action %(name)s applied a suspension.',
            name=self.name,
        )
        if self.effective_date:
            reason += '\n' + _('Effective date: %(date)s.', date=self.effective_date)
        if self.violation_id:
            reason += '\n' + _('Related violation: %(violation)s.', violation=self.violation_id.display_name)
        self.federation_id.write({
            'federation_status': 'suspended',
            'suspension_reason': reason,
        })
        self.federation_id.message_post(body=_(
            'Federation suspended by legal action %(action)s.',
            action=self.name,
        ))

    def _lift_federation_suspension_if_resolved(self):
        """Reactivate the federation only when this was the active suspension."""
        self.ensure_one()
        other_active_suspension = self.search_count([
            ('id', '!=', self.id),
            ('federation_id', '=', self.federation_id.id),
            ('action_type', '=', 'suspension'),
            ('state', '=', 'applied'),
        ])
        current_reason = self.federation_id.suspension_reason or ''
        if not other_active_suspension and self.name in current_reason:
            self.federation_id.write({
                'federation_status': 'active',
                'suspension_reason': False,
            })
            self.federation_id.message_post(body=_(
                'Suspension lifted after closing legal action %(action)s.',
                action=self.name,
            ))
