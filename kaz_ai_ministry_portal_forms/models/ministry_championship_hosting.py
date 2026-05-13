# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import timedelta


class MinistryChampionshipHosting(models.Model):
    """Championship hosting application submitted by federations.

    Federations submit this form via the portal at least 30 days before the event.
    """
    _name = 'ministry.championship.hosting'
    _description = 'Championship Hosting Application'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        default=lambda self: _('New'),
        help='Auto-generated hosting application reference.',
    )
    federation_id = fields.Many2one(
        'res.partner',
        string='Federation',
        required=True,
        domain=[('is_federation', '=', True)],
        tracking=True,
        help='Federation applying to host this championship.',
    )
    championship_name = fields.Char(
        string='Championship Name',
        required=True,
        help='Full official name of the hosted championship.',
    )
    championship_level = fields.Selection(
        selection=[
            ('local', 'Local'),
            ('arab', 'Arab'),
            ('regional', 'Regional'),
            ('asian', 'Asian'),
            ('international', 'International'),
        ],
        string='Level',
        required=True,
        help='Geographic or competitive scope of the event to be hosted.',
    )
    event_date_start = fields.Date(
        string='Event Start Date',
        required=True,
        help='First day of the hosted championship.',
    )
    event_date_end = fields.Date(
        string='Event End Date',
        required=True,
        help='Last day of the hosted championship.',
    )
    venue = fields.Char(
        string='Venue',
        required=True,
        help='Name and address of the event venue.',
    )
    expected_participants = fields.Integer(
        string='Expected Participants',
        required=True,
        help='Total number of athletes, officials, and support staff expected.',
    )
    expected_countries = fields.Integer(
        string='Expected Countries',
        default=1,
        help='Number of countries expected to participate.',
    )
    hosting_budget = fields.Monetary(
        string='Hosting Budget (AED)',
        currency_field='currency_id',
        required=True,
        help='Total estimated cost of hosting the championship.',
    )
    venue_capacity = fields.Integer(
        string='Venue Capacity (Seats)',
        help='Maximum spectator capacity of the venue.',
    )
    notes = fields.Text(
        string='Additional Notes',
        help='Logistics, special requirements, or other relevant information.',
    )
    submission_deadline = fields.Date(
        string='Submission Deadline',
        compute='_compute_submission_deadline',
        store=True,
        help='Hosting applications must be submitted at least 30 days before the event.',
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('under_review', 'Under Review'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
        help='Lifecycle state of the hosting application.',
    )
    sport_type = fields.Char(
        string='Sport',
        help='Type of sport for the hosted championship.',
    )
    organizer = fields.Char(
        string='Organizing Body',
        help='International federation or body officially organizing the event.',
    )
    participant_categories = fields.Char(
        string='Participant Categories',
        help='Gender/age categories (e.g., Men / Women / Youth).',
    )
    funding_sources = fields.Text(
        string='Funding Sources',
        help='Sources of funding covering hosting costs (ticket sales, sponsorships, Ministry grant, etc.).',
    )
    expected_return = fields.Text(
        string='Expected Return from Hosting',
        help='Expected strategic, financial, or reputational benefits from hosting this championship.',
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

    @api.depends('event_date_start')
    def _compute_submission_deadline(self):
        for rec in self:
            if rec.event_date_start:
                rec.submission_deadline = rec.event_date_start - timedelta(days=30)
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

    @api.constrains('expected_participants', 'expected_countries', 'hosting_budget', 'venue_capacity')
    def _check_values(self):
        for rec in self:
            if rec.expected_participants <= 0:
                raise ValidationError(_('Expected participants must be greater than zero.'))
            if rec.expected_countries <= 0:
                raise ValidationError(_('Expected countries must be greater than zero.'))
            if rec.hosting_budget < 0:
                raise ValidationError(_('Hosting budget cannot be negative.'))
            if rec.venue_capacity < 0:
                raise ValidationError(_('Venue capacity cannot be negative.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('ministry.championship.hosting') or _('New')
        return super().create(vals_list)

    def action_print_hosting(self):
        """Return PDF report action for this hosting application."""
        return self.env.ref('kaz_ai_ministry_portal_forms.action_report_hosting').report_action(self)

    def action_submit(self):
        """Submit the hosting application."""
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError(_('Only draft hosting applications can be submitted.'))
            if not rec.event_date_start:
                raise ValidationError(_('Event start date is required.'))
            if fields.Date.today() > (rec.event_date_start - timedelta(days=30)):
                raise ValidationError(
                    _('Hosting applications must be submitted at least 30 days before the event start date.')
                )
            rec.write({'state': 'submitted'})
            rec.message_post(body=_(
                'Hosting application %(name)s submitted for %(championship)s.',
                name=rec.name,
                championship=rec.championship_name,
            ))

    def action_review(self):
        """Take the hosting application under review."""
        for rec in self:
            if rec.state != 'submitted':
                raise ValidationError(_('Only submitted hosting applications can be taken under review.'))
            rec.write({'state': 'under_review'})

    def action_approve(self):
        """Approve the hosting application."""
        for rec in self:
            if rec.state != 'under_review':
                raise ValidationError(_('Only hosting applications under review can be approved.'))
            rec.write({'state': 'approved'})
            rec.message_post(body=_('Hosting application approved by Ministry.'))

    def action_reject(self):
        """Reject the hosting application."""
        for rec in self:
            if rec.state not in ('submitted', 'under_review'):
                raise ValidationError(_('Only submitted or under-review hosting applications can be rejected.'))
            rec.write({'state': 'rejected'})
            rec.message_post(body=_('Hosting application rejected.'))
