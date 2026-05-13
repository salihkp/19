# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import timedelta


class MinistryPostEventReport(models.Model):
    """Post-event report submitted by federation after championship.

    Must be submitted within 15 days after the event end date.
    The achievement_pct field is used by the risk scorer to evaluate performance.
    """
    _name = 'ministry.post.event.report'
    _description = 'Post-Event Report'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        default=lambda self: _('New'),
        help='Auto-generated post-event report reference.',
    )
    federation_id = fields.Many2one(
        'res.partner',
        string='Federation',
        required=True,
        domain=[('is_federation', '=', True)],
        tracking=True,
        help='Federation submitting this post-event report.',
    )
    event_name = fields.Char(
        string='Event Name',
        required=True,
        help='Name of the championship or event this report covers.',
    )
    event_date_start = fields.Date(
        string='Event Start Date',
        required=True,
        help='First day of the event.',
    )
    event_date_end = fields.Date(
        string='Event End Date',
        required=True,
        help='Last day of the event.',
    )
    submission_deadline = fields.Date(
        string='Submission Deadline',
        compute='_compute_submission_deadline',
        store=True,
        help='Reports must be submitted within 15 days of the event end date.',
    )
    athletes_participated = fields.Integer(
        string='Athletes Who Participated',
        required=True,
        help='Actual number of athletes who competed.',
    )
    medals_gold = fields.Integer(string='Gold Medals', default=0)
    medals_silver = fields.Integer(string='Silver Medals', default=0)
    medals_bronze = fields.Integer(string='Bronze Medals', default=0)
    final_rank = fields.Integer(
        string='Overall Ranking',
        help='Federation\'s overall ranking among participating countries/teams.',
    )
    achievement_pct = fields.Float(
        string='Achievement %',
        digits=(5, 2),
        help='Overall achievement percentage vs pre-event goals (0–100). Used by risk scorer.',
    )
    actual_expenditure = fields.Monetary(
        string='Actual Expenditure (AED)',
        currency_field='currency_id',
        help='Total actual spending on the event.',
    )
    submitted_on = fields.Date(
        string='Submitted On',
        readonly=True,
        copy=False,
        help='Date on which the federation submitted the report.',
    )
    support_request_id = fields.Many2one(
        'ministry.support.request',
        string='Related Support Request',
        domain="[('federation_id', '=', federation_id)]",
        help='Support request this report closes out.',
    )
    narrative = fields.Html(
        string='Event Narrative',
        help='Detailed description of the event, outcomes, and lessons learned.',
    )
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'ministry_per_attachment_rel',
        'report_id',
        'attachment_id',
        string='Attachments',
        help='Supporting documents, photos, and official results.',
    )
    reviewed_by = fields.Many2one(
        'res.users',
        string='Reviewed By',
        readonly=True,
        help='Ministry officer who reviewed this report.',
    )
    review_date = fields.Date(
        string='Review Date',
        readonly=True,
        help='Date on which the report was formally reviewed.',
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('accepted', 'Accepted'),
            ('rejected', 'Rejected'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
        help='Lifecycle state of the post-event report.',
    )
    is_late = fields.Boolean(
        string='Submitted Late',
        compute='_compute_is_late',
        store=True,
        help='True if the report was submitted after the 15-day deadline.',
    )
    sport_type = fields.Char(
        string='Sport',
        help='Type of sport covered in this report.',
    )
    event_location = fields.Char(
        string='Event Location',
        help='City and country where the event took place.',
    )
    countries_count = fields.Integer(
        string='Participating Countries',
        help='Total number of countries that participated.',
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
        string='Championship Level',
        help='Geographic or competitive scope of the event.',
    )
    goals_achieved = fields.Text(
        string='Goals Achieved',
        help='Specific goals that were achieved through participation.',
    )
    challenges = fields.Text(
        string='Challenges',
        help='Challenges faced during participation, if any.',
    )
    recommendations = fields.Text(
        string='Recommendations',
        help='Recommendations for the Ministry and federation for future participation.',
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

    @api.depends('event_date_end')
    def _compute_submission_deadline(self):
        for rec in self:
            if rec.event_date_end:
                rec.submission_deadline = rec.event_date_end + timedelta(days=15)
            else:
                rec.submission_deadline = False

    @api.depends('submission_deadline', 'submitted_on')
    def _compute_is_late(self):
        for rec in self:
            rec.is_late = bool(
                rec.submitted_on
                and rec.submission_deadline
                and rec.submitted_on > rec.submission_deadline
            )

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

    @api.constrains('support_request_id', 'federation_id')
    def _check_support_request_federation(self):
        for rec in self:
            if rec.support_request_id and rec.support_request_id.federation_id != rec.federation_id:
                raise ValidationError(_('The support request must belong to the same federation.'))

    @api.constrains(
        'athletes_participated', 'medals_gold', 'medals_silver', 'medals_bronze',
        'final_rank', 'actual_expenditure',
    )
    def _check_values(self):
        for rec in self:
            if rec.athletes_participated <= 0:
                raise ValidationError(_('Athletes participated must be greater than zero.'))
            if rec.medals_gold < 0 or rec.medals_silver < 0 or rec.medals_bronze < 0:
                raise ValidationError(_('Medal counts cannot be negative.'))
            if rec.final_rank < 0:
                raise ValidationError(_('Final rank cannot be negative.'))
            if rec.actual_expenditure < 0:
                raise ValidationError(_('Actual expenditure cannot be negative.'))

    @api.constrains('achievement_pct')
    def _check_achievement_pct(self):
        for rec in self:
            if rec.achievement_pct < 0 or rec.achievement_pct > 100:
                raise ValidationError(_('Achievement percentage must be between 0 and 100.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('ministry.post.event.report') or _('New')
        return super().create(vals_list)

    def action_print_per(self):
        """Return PDF report action for this post-event report."""
        return self.env.ref('kaz_ai_ministry_portal_forms.action_report_per').report_action(self)

    def action_submit(self):
        """Submit the post-event report."""
        for rec in self:
            if rec.state not in ('draft', 'rejected'):
                raise ValidationError(_('Only draft or rejected post-event reports can be submitted.'))
            rec.write({
                'state': 'submitted',
                'submitted_on': fields.Date.today(),
            })
            rec.message_post(body=_(
                'Post-event report %(name)s submitted for %(event)s.',
                name=rec.name,
                event=rec.event_name,
            ))

    def action_accept(self):
        """Accept the report after review."""
        for rec in self:
            if rec.state != 'submitted':
                raise ValidationError(_('Only submitted post-event reports can be accepted.'))
            rec.write({
                'state': 'accepted',
                'reviewed_by': self.env.user.id,
                'review_date': fields.Date.today(),
            })
            rec.message_post(body=_(
                'Post-event report accepted by %(user)s.',
                user=self.env.user.name,
            ))
            # Close the linked support request if awaiting report
            if rec.support_request_id and rec.support_request_id.state == 'awaiting_report':
                rec.support_request_id.action_close()

    def action_reject(self):
        """Reject the report, requiring resubmission."""
        for rec in self:
            if rec.state != 'submitted':
                raise ValidationError(_('Only submitted post-event reports can be rejected.'))
            rec.write({'state': 'rejected'})
            rec.message_post(body=_('Post-event report rejected. Please resubmit with corrections.'))
