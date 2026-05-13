# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # ── Federation Identification ────────────────────────────────────────────
    is_federation = fields.Boolean(
        string='Is Federation',
        default=False,
        help='Flag this partner as a sports federation registered with the Ministry.',
    )
    sport_id = fields.Many2one(
        'ministry.sport',
        string='Sport',
        help='The sport this federation governs.',
    )
    sport_type = fields.Selection(
        [('individual', 'Individual'), ('team', 'Team')],
        string='Sport Type',
        help='Whether the sport is individual or team-based.',
    )
    olympic_classification = fields.Selection(
        [('olympic', 'Olympic'), ('non_olympic', 'Non-Olympic')],
        string='Olympic Classification',
        help='Whether the sport is part of the Olympic programme.',
    )

    # ── Membership Statistics ────────────────────────────────────────────────
    registered_players_count = fields.Integer(
        string='Registered Players',
        help='Total number of registered players under this federation.',
    )
    male_players_count = fields.Integer(
        string='Male Players',
        compute='_compute_male_players_count',
        store=True,
        help='Number of registered male players.',
    )
    female_players_count = fields.Integer(
        string='Female Players',
        help='Number of registered female players.',
    )
    junior_players_count = fields.Integer(
        string='Junior Players (U18)',
        help='Number of registered junior players under 18.',
    )
    senior_players_count = fields.Integer(
        string='Senior Players',
        compute='_compute_senior_players_count',
        store=True,
        help='Number of registered senior players (18 and above).',
    )

    # ── Affiliated Clubs ─────────────────────────────────────────────────────
    affiliated_clubs_ids = fields.One2many(
        'ministry.club',
        'federation_id',
        string='Affiliated Clubs',
        help='Clubs officially affiliated with this federation.',
    )
    affiliated_clubs_count = fields.Integer(
        string='Clubs',
        compute='_compute_affiliated_clubs_count',
        help='Total number of affiliated clubs.',
    )

    # ── Status ───────────────────────────────────────────────────────────────
    federation_status = fields.Selection(
        [('active', 'Active'), ('suspended', 'Suspended')],
        string='Federation Status',
        default='active',
        tracking=True,
        help='Active: fully operational. Suspended: access and payments restricted.',
    )
    suspension_reason = fields.Text(
        string='Suspension Reason',
        help='Reason for suspension — required when status is set to Suspended.',
    )

    # ── Risk Indicators (populated by kaz_ai_ministry_risk_scoring) ──────────
    risk_score = fields.Float(
        string='Risk Score',
        default=0.0,
        help='Composite risk score (0–100). Computed by the risk scoring engine.',
    )
    risk_level = fields.Selection(
        [('low', 'Low'), ('medium', 'Medium'), ('high', 'High')],
        string='Risk Level',
        default='low',
        help='Low: <35 | Medium: 35–65 | High: >65. Computed by the risk scoring engine.',
    )

    # ── Smart Button Counts ──────────────────────────────────────────────────
    support_request_count = fields.Integer(
        string='Support Requests',
        compute='_compute_support_counts',
        help='Total support requests submitted by this federation.',
    )
    approved_ytd_amount = fields.Float(
        string='Approved YTD (AED)',
        compute='_compute_support_counts',
        help='Total approved support amount for the current fiscal year.',
    )
    inspection_count = fields.Integer(
        string='Inspections',
        compute='_compute_inspection_count',
        help='Number of inspection visits for this federation.',
    )

    def _compute_affiliated_clubs_count(self):
        for partner in self:
            partner.affiliated_clubs_count = len(partner.affiliated_clubs_ids)

    @api.depends('registered_players_count', 'female_players_count')
    def _compute_male_players_count(self):
        for partner in self:
            partner.male_players_count = max(
                partner.registered_players_count - partner.female_players_count,
                0,
            )

    @api.depends('registered_players_count', 'junior_players_count')
    def _compute_senior_players_count(self):
        for partner in self:
            partner.senior_players_count = max(
                partner.registered_players_count - partner.junior_players_count,
                0,
            )

    @api.constrains('registered_players_count', 'female_players_count', 'junior_players_count')
    def _check_player_statistics(self):
        for partner in self.filtered('is_federation'):
            counts = {
                _('Registered Players'): partner.registered_players_count,
                _('Female Players'): partner.female_players_count,
                _('Junior Players'): partner.junior_players_count,
            }
            negative = [label for label, value in counts.items() if value < 0]
            if negative:
                raise ValidationError(_(
                    'Player statistics cannot contain negative values: %(fields)s.',
                    fields=', '.join(negative),
                ))
            if partner.female_players_count > partner.registered_players_count:
                raise ValidationError(_(
                    'Female players cannot exceed total registered players.'
                ))
            if partner.junior_players_count > partner.registered_players_count:
                raise ValidationError(_(
                    'Junior players cannot exceed total registered players.'
                ))

    def _compute_support_counts(self):
        """Compute request count and approved YTD amount for smart buttons."""
        try:
            Request = self.env['ministry.support.request']
        except KeyError:
            for partner in self:
                partner.support_request_count = 0
                partner.approved_ytd_amount = 0.0
            return
        fiscal_year = self.env['ir.config_parameter'].sudo().get_param(
            'ministry.fiscal_year', '2026'
        )
        for partner in self:
            if not partner.is_federation:
                partner.support_request_count = 0
                partner.approved_ytd_amount = 0.0
                continue
            requests = Request.search([('federation_id', '=', partner.id)])
            partner.support_request_count = len(requests)
            approved = Request.search([
                ('federation_id', '=', partner.id),
                ('state', 'in', ['approved', 'to_pay', 'paid', 'awaiting_report', 'closed']),
                ('fiscal_year', '=', fiscal_year),
            ])
            partner.approved_ytd_amount = sum(approved.mapped('approved_amount'))

    def _compute_inspection_count(self):
        try:
            Inspection = self.env['ministry.inspection']
        except KeyError:
            for partner in self:
                partner.inspection_count = 0
            return
        for partner in self:
            if not partner.is_federation:
                partner.inspection_count = 0
                continue
            partner.inspection_count = Inspection.search_count([
                ('federation_id', '=', partner.id),
            ])

    def action_open_support_requests(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Support Requests',
            'res_model': 'ministry.support.request',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [('federation_id', '=', self.id)],
            'context': {'default_federation_id': self.id},
        }

    def action_open_inspections(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Inspections',
            'res_model': 'ministry.inspection',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [('federation_id', '=', self.id)],
            'context': {'default_federation_id': self.id},
        }

    def action_open_clubs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Affiliated Clubs',
            'res_model': 'ministry.club',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [('federation_id', '=', self.id)],
            'context': {'default_federation_id': self.id},
        }

    @api.onchange('federation_status')
    def _onchange_federation_status(self):
        if self.federation_status == 'active':
            self.suspension_reason = False
