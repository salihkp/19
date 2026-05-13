# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import timedelta


class MinistryChampionshipParticipation(models.Model):
    """Championship participation application submitted by federations.

    Federations submit this form via the portal at least 15 days before the event.
    """
    _name = 'ministry.championship.participation'
    _description = 'Championship Participation Application'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        default=lambda self: _('New'),
        help='Auto-generated application reference.',
    )
    federation_id = fields.Many2one(
        'res.partner',
        string='Federation',
        required=True,
        domain=[('is_federation', '=', True)],
        tracking=True,
        help='Federation submitting this participation application.',
    )
    championship_name = fields.Char(
        string='Championship Name',
        required=True,
        help='Full official name of the championship or tournament.',
    )
    championship_level = fields.Selection(
        selection=[
            ('local', 'Local'),
            ('arab', 'Arab'),
            ('regional', 'Regional'),
            ('asian', 'Asian'),
            ('international', 'International'),
            ('olympic', 'Olympic'),
        ],
        string='Level',
        required=True,
        help='Geographic or competitive level of the event.',
    )
    event_date_start = fields.Date(
        string='Event Start Date',
        required=True,
        help='First day of the championship.',
    )
    event_date_end = fields.Date(
        string='Event End Date',
        required=True,
        help='Last day of the championship.',
    )
    location = fields.Char(
        string='Location (City, Country)',
        required=True,
        help='City and country where the event takes place.',
    )
    athletes_count = fields.Integer(
        string='Number of Athletes',
        required=True,
        help='Total number of athletes expected to participate.',
    )
    officials_count = fields.Integer(
        string='Number of Officials',
        default=0,
        help='Coaching staff, team managers, and medical personnel.',
    )
    estimated_budget = fields.Monetary(
        string='Estimated Budget (AED)',
        currency_field='currency_id',
        required=True,
        help='Total estimated cost of participation.',
    )
    budget_line_ids = fields.One2many(
        'ministry.championship.participation.budget.line',
        'participation_id',
        string='Estimated Budget Breakdown',
        copy=True,
        help='Detailed estimated participation costs by expense category.',
    )
    budget_line_total = fields.Monetary(
        string='Budget Line Total (AED)',
        currency_field='currency_id',
        compute='_compute_budget_line_total',
        store=True,
        help='Total of all detailed budget lines.',
    )
    notes = fields.Text(
        string='Additional Notes',
        help='Any additional information supporting the application.',
    )
    support_request_id = fields.Many2one(
        'ministry.support.request',
        string='Support Request',
        readonly=True,
        copy=False,
        help='Support request generated from this participation application.',
    )
    submission_deadline = fields.Date(
        string='Submission Deadline',
        compute='_compute_submission_deadline',
        store=True,
        help='Applications must be submitted at least 15 days before the event.',
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('acknowledged', 'Acknowledged'),
            ('rejected', 'Rejected'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
        help='Lifecycle state of the participation application.',
    )
    sport_type = fields.Char(
        string='Sport',
        help='Type of sport for this championship (e.g., Football, Swimming).',
    )
    participation_category = fields.Selection(
        selection=[
            ('men', 'Men'),
            ('women', 'Women'),
            ('youth', 'Youth'),
            ('mixed', 'All / Mixed'),
        ],
        string='Participation Category',
        help='Gender/age category of participants.',
    )
    countries_count = fields.Integer(
        string='Number of Countries',
        help='Total number of countries participating in this championship.',
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
    )
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True,
    )

    @api.depends('budget_line_ids.total_amount')
    def _compute_budget_line_total(self):
        for rec in self:
            rec.budget_line_total = sum(rec.budget_line_ids.mapped('total_amount'))

    @api.depends('event_date_start')
    def _compute_submission_deadline(self):
        for rec in self:
            if rec.event_date_start:
                rec.submission_deadline = rec.event_date_start - timedelta(days=15)
            else:
                rec.submission_deadline = False

    @api.constrains('event_date_start', 'event_date_end')
    def _check_dates(self):
        for rec in self:
            if rec.event_date_start and rec.event_date_end:
                if rec.event_date_end < rec.event_date_start:
                    raise ValidationError(_('Event end date must be after start date.'))

    @api.constrains('federation_id')
    def _check_federation(self):
        for rec in self:
            if rec.federation_id and not rec.federation_id.is_federation:
                raise ValidationError(_('The selected partner must be a federation.'))

    @api.constrains('athletes_count', 'officials_count', 'estimated_budget')
    def _check_values(self):
        for rec in self:
            if rec.athletes_count <= 0:
                raise ValidationError(_('Number of athletes must be greater than zero.'))
            if rec.officials_count < 0:
                raise ValidationError(_('Number of officials cannot be negative.'))
            if rec.estimated_budget < 0:
                raise ValidationError(_('Estimated budget cannot be negative.'))

    @api.constrains('budget_line_ids', 'estimated_budget')
    def _check_budget_lines(self):
        for rec in self:
            if rec.budget_line_ids and rec.budget_line_total <= 0:
                raise ValidationError(_('At least one budget line must have an amount greater than zero.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('ministry.championship.participation') or _('New')
        return super().create(vals_list)

    def action_print_participation(self):
        """Return PDF report action for this participation application."""
        return self.env.ref('kaz_ai_ministry_portal_forms.action_report_participation').report_action(self)

    def action_submit(self):
        """Submit the participation application."""
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError(_('Only draft participation applications can be submitted.'))
            if not rec.event_date_start:
                raise ValidationError(_('Event start date is required.'))
            if fields.Date.today() > (rec.event_date_start - timedelta(days=15)):
                raise ValidationError(
                    _('Applications must be submitted at least 15 days before the event start date.')
                )
            rec.write({'state': 'submitted'})
            rec.message_post(body=_(
                'Participation application %(name)s submitted for %(championship)s.',
                name=rec.name,
                championship=rec.championship_name,
            ))

    def action_acknowledge(self):
        """Acknowledge the application."""
        for rec in self:
            if rec.state != 'submitted':
                raise ValidationError(_('Only submitted participation applications can be acknowledged.'))
            rec.write({'state': 'acknowledged'})
            rec.message_post(body=_('Application acknowledged by Ministry.'))

    def action_reject(self):
        """Reject the application."""
        for rec in self:
            if rec.state != 'submitted':
                raise ValidationError(_('Only submitted participation applications can be rejected.'))
            rec.write({'state': 'rejected'})
            rec.message_post(body=_('Application rejected.'))


class MinistryChampionshipParticipationBudgetLine(models.Model):
    """Estimated budget line for a championship participation application."""
    _name = 'ministry.championship.participation.budget.line'
    _description = 'Participation Estimated Budget Line'
    _order = 'participation_id, sequence, id'

    participation_id = fields.Many2one(
        'ministry.championship.participation',
        string='Participation Application',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(default=10)
    expense_group = fields.Selection(
        selection=[
            ('fees', 'Fees'),
            ('travel_tickets', 'Travel Tickets'),
            ('accommodation_meals', 'Accommodation and Meals'),
            ('pocket_money', 'Pocket Money'),
            ('other_expenses', 'Other Expenses'),
        ],
        string='Expense Category',
        required=True,
    )
    description = fields.Char(
        string='Description',
        required=True,
    )
    quantity = fields.Float(
        string='Quantity',
        default=1.0,
        digits=(16, 2),
    )
    unit_amount = fields.Monetary(
        string='Unit Amount (AED)',
        currency_field='currency_id',
    )
    total_amount = fields.Monetary(
        string='Total (AED)',
        currency_field='currency_id',
        compute='_compute_total_amount',
        store=True,
    )
    currency_id = fields.Many2one(
        related='participation_id.currency_id',
        store=True,
        readonly=True,
    )
    federation_id = fields.Many2one(
        related='participation_id.federation_id',
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        related='participation_id.company_id',
        store=True,
        readonly=True,
    )

    @api.depends('quantity', 'unit_amount')
    def _compute_total_amount(self):
        for line in self:
            line.total_amount = line.quantity * line.unit_amount

    @api.constrains('quantity', 'unit_amount')
    def _check_amounts(self):
        for line in self:
            if line.quantity < 0:
                raise ValidationError(_('Quantity cannot be negative.'))
            if line.unit_amount < 0:
                raise ValidationError(_('Unit amount cannot be negative.'))
