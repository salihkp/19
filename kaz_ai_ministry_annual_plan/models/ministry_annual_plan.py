# -*- coding: utf-8 -*-
from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MinistryAnnualPlan(models.Model):
    _name = 'ministry.annual.plan'
    _description = 'Annual Support Plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'fiscal_year desc, federation_id'

    name = fields.Char(
        string='Plan Reference',
        required=True,
        tracking=True,
        help='Human-readable reference for this plan (e.g., FY2026-FOOTBALL).',
    )
    fiscal_year = fields.Char(
        string='Fiscal Year',
        required=True,
        tracking=True,
        default=lambda self: self.env['ir.config_parameter'].sudo().get_param(
            'ministry.fiscal_year', '2026'
        ),
        help='The fiscal year this plan covers (e.g., 2026).',
    )
    federation_id = fields.Many2one(
        'res.partner',
        string='Federation',
        required=True,
        domain="[('is_federation', '=', True)]",
        tracking=True,
        help='The federation this plan belongs to.',
    )
    state = fields.Selection(
        [('draft', 'Draft'), ('submitted', 'Submitted'), ('approved', 'Approved')],
        string='Status',
        default='draft',
        tracking=True,
        help='Draft: being prepared. Submitted: sent to Ministry. Approved: endorsed by Ministry.',
    )
    estimated_budget = fields.Float(
        string='Estimated Budget (AED)',
        digits=(16, 2),
        help='Total estimated budget for all planned activities this year.',
    )
    total_plan_amount = fields.Float(
        string='Total Planned (AED)',
        compute='_compute_totals',
        store=True,
        digits=(16, 2),
        help='Sum of all activity line estimated amounts.',
    )
    plan_line_ids = fields.One2many(
        'ministry.annual.plan.line',
        'plan_id',
        string='Planned Activities',
        help='Individual activity lines — each maps to a support item.',
    )
    kpi_line_ids = fields.One2many(
        'ministry.annual.plan.kpi',
        'plan_id',
        string='Key Performance Indicators',
        help='Performance targets the federation commits to achieve this year.',
    )
    submission_date = fields.Date(string='Submission Date', readonly=True)
    approval_date = fields.Date(string='Approval Date', readonly=True)
    budget_analytic_id = fields.Many2one(
        'budget.analytic',
        string='Odoo Budget',
        readonly=True,
        copy=False,
        help='Linked Odoo Budget created from the approved annual plan.',
    )
    budget_state = fields.Selection(
        related='budget_analytic_id.state',
        string='Budget Status',
        readonly=True,
    )
    budget_line_count = fields.Integer(
        string='Budget Lines',
        compute='_compute_budget_line_count',
    )
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
    )

    @api.depends('plan_line_ids.estimated_amount')
    def _compute_totals(self):
        for plan in self:
            plan.total_plan_amount = sum(plan.plan_line_ids.mapped('estimated_amount'))

    def _compute_budget_line_count(self):
        for plan in self:
            plan.budget_line_count = len(plan.budget_analytic_id.budget_line_ids)

    def action_submit(self):
        """Submit the annual plan to the Ministry for review."""
        for plan in self:
            if plan.state != 'draft':
                raise UserError('Only draft annual plans can be submitted.')
            if not plan.plan_line_ids:
                raise UserError('Cannot submit a plan with no activity lines.')
            plan.write({
                'state': 'submitted',
                'submission_date': fields.Date.today(),
            })
            plan.message_post(body=_(
                'Annual plan submitted for Ministry review on %(date)s.',
                date=fields.Date.today().strftime('%d/%m/%Y'),
            ))

    def action_approve(self):
        """Approve the annual plan and open the linked Odoo analytic budget."""
        for plan in self:
            if plan.state != 'submitted':
                raise UserError('Only submitted annual plans can be approved.')
            if not plan.plan_line_ids:
                raise UserError('Cannot approve a plan with no activity lines.')
            budget = plan._sync_odoo_budget(open_budget=True)
            plan.write({
                'state': 'approved',
                'approval_date': fields.Date.today(),
            })
            plan.message_post(body=_(
                'Annual plan approved on %(date)s and linked to Odoo Budget %(budget)s.',
                date=fields.Date.today().strftime('%d/%m/%Y'),
                budget=budget.display_name,
            ))

    def action_reset_to_draft(self):
        for plan in self:
            if plan.state == 'draft':
                raise UserError('This annual plan is already in draft.')
            plan.write({'state': 'draft'})

    def action_sync_budget(self):
        for plan in self:
            if plan.state != 'approved':
                raise UserError('Only approved annual plans can be synced to Odoo Budget.')
            plan._sync_odoo_budget(open_budget=True)
        return True

    def action_open_budget(self):
        self.ensure_one()
        if not self.budget_analytic_id:
            raise UserError('No Odoo Budget is linked to this annual plan yet.')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Odoo Budget'),
            'res_model': 'budget.analytic',
            'res_id': self.budget_analytic_id.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
        }

    def _sync_odoo_budget(self, open_budget=False):
        self.ensure_one()
        if 'budget.analytic' not in self.env or 'budget.line' not in self.env:
            raise UserError('Install the Odoo Budget Management module (account_budget) before approving annual plans.')

        date_from, date_to = self._budget_period()
        budget_vals = {
            'name': _('Ministry Support Budget %(year)s - %(federation)s', year=self.fiscal_year, federation=self.federation_id.display_name),
            'date_from': date_from,
            'date_to': date_to,
            'budget_type': 'expense',
            'company_id': self.company_id.id,
            'user_id': self.env.user.id,
        }
        Budget = self.env['budget.analytic'].sudo()
        BudgetLine = self.env['budget.line'].sudo()

        budget = self.budget_analytic_id.sudo()
        if budget and budget.state != 'draft':
            self.message_post(body=_(
                'Linked Odoo Budget %(budget)s is already %(state)s. Existing budget lines were kept unchanged.',
                budget=budget.display_name,
                state=budget.state,
            ))
            return budget

        if budget:
            budget.write(budget_vals)
            budget.budget_line_ids.unlink()
        else:
            budget = Budget.create(budget_vals)
            self.write({'budget_analytic_id': budget.id})

        line_vals = [
            self._prepare_budget_line_vals(line, budget)
            for line in self.plan_line_ids
            if line.estimated_amount
        ]
        if not line_vals:
            raise UserError('At least one annual plan line must have an estimated amount.')
        BudgetLine.create(line_vals)

        if open_budget and budget.state == 'draft':
            budget.action_budget_confirm()
        return budget

    def _prepare_budget_line_vals(self, line, budget):
        BudgetLine = self.env['budget.line']
        vals = {
            'budget_analytic_id': budget.id,
            'sequence': line.sequence,
            'budget_amount': line.estimated_amount,
        }
        for account in self._budget_analytic_accounts(line):
            field_name = account.plan_id._column_name()
            if field_name in BudgetLine._fields:
                vals[field_name] = account.id
        return vals

    def _budget_analytic_accounts(self, line=None):
        accounts = self.env['account.analytic.account']
        accounts |= self._get_or_create_analytic_account(
            'Federation',
            self._clean_federation_name(self.federation_id.display_name),
            self._federation_analytic_code(),
        )
        if line and line.category:
            category_label, category_code = self._category_analytic_values(line.category)
            accounts |= self._get_or_create_analytic_account('Support Category', category_label, category_code)
        accounts |= self._get_or_create_analytic_account('Fiscal Year', f'FY{self.fiscal_year}', f'FY-{self.fiscal_year}')
        return accounts

    def _get_or_create_analytic_account(self, plan_name, account_name, account_code):
        plan = self._get_or_create_analytic_plan(plan_name)
        Account = self.env['account.analytic.account'].sudo()
        account = Account.search([
            ('plan_id', 'child_of', plan.id),
            ('code', '=', account_code),
            ('company_id', 'in', [False, self.company_id.id]),
        ], limit=1)
        if not account:
            account = Account.search([
                ('plan_id', 'child_of', plan.id),
                ('name', '=', account_name),
                ('company_id', 'in', [False, self.company_id.id]),
            ], limit=1)
        if not account:
            account = Account.create({
                'name': account_name,
                'code': account_code,
                'plan_id': plan.id,
                'company_id': False,
            })
        return account

    def _get_or_create_analytic_plan(self, name):
        Plan = self.env['account.analytic.plan'].sudo()
        plan = Plan.search([('name', '=', name)], limit=1)
        if not plan:
            plan = Plan.create({'name': name, 'default_applicability': 'optional'})
        return plan

    def _budget_period(self):
        try:
            year = int(self.fiscal_year)
        except (TypeError, ValueError):
            raise UserError('Fiscal Year must be a four-digit year before creating an Odoo Budget.')
        return date(year, 1, 1), date(year, 12, 31)

    def _federation_analytic_code(self):
        sport_code = (self.federation_id.sport_id.code or '').upper().replace(' ', '-')
        if sport_code:
            return f'FED-{sport_code}'
        return f'FED-{self.federation_id.id}'

    def _category_analytic_values(self, category):
        values = {
            'operational': ('Operational Support', 'CAT-OP'),
            'technical': ('Technical Support', 'CAT-TEC'),
            'general': ('General Financial Support', 'CAT-GEN'),
            'activity': ('Activity Support', 'CAT-ACT'),
        }
        return values.get(category, ('Other Support', 'CAT-OTHER'))

    def _clean_federation_name(self, name):
        cleaned = (name or 'Federation').replace(' Federation Admin', ' Federation').replace(' Admin', '')
        return cleaned if cleaned.startswith('UAE ') else f'UAE {cleaned}'


class MinistryAnnualPlanLine(models.Model):
    _name = 'ministry.annual.plan.line'
    _description = 'Annual Plan Activity Line'
    _order = 'sequence, support_item_id'

    plan_id = fields.Many2one(
        'ministry.annual.plan',
        string='Plan',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(default=10)
    support_item_id = fields.Many2one(
        'ministry.support.item',
        string='Support Item',
        required=True,
        help='The catalog item this activity line refers to.',
    )
    description = fields.Char(
        string='Activity Description',
        help='Specific details about this planned activity.',
    )
    quantity = fields.Float(
        string='Quantity / Count',
        default=1.0,
        help='Number of units, events, or occurrences planned.',
    )
    estimated_amount = fields.Float(
        string='Estimated Amount (AED)',
        digits=(16, 2),
        required=True,
        help='Estimated AED cost for this activity.',
    )
    target_kpi = fields.Char(
        string='Target KPI',
        help='Expected performance outcome for this activity (e.g., "Win 2 medals").',
    )
    category = fields.Selection(related='support_item_id.category', store=True)
    company_id = fields.Many2one(related='plan_id.company_id', store=True)


class MinistryAnnualPlanKpi(models.Model):
    _name = 'ministry.annual.plan.kpi'
    _description = 'Annual Plan KPI'
    _order = 'name'

    plan_id = fields.Many2one(
        'ministry.annual.plan',
        string='Plan',
        required=True,
        ondelete='cascade',
    )
    name = fields.Char(string='KPI Name', required=True,
        help='Name of the performance indicator (e.g., "Gold Medals", "Player Registrations").')
    target_value = fields.Float(string='Target Value', required=True,
        help='Numeric target for this KPI.')
    unit = fields.Char(string='Unit', help='Unit of measurement (e.g., medals, players, tournaments).')
    achieved_value = fields.Float(string='Achieved Value',
        help='Actual value achieved — filled in post-event reports.')
    company_id = fields.Many2one(related='plan_id.company_id', store=True)
