# -*- coding: utf-8 -*-
import logging
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

STATES = [
    ('draft',           'Draft'),
    ('submitted',       'Submitted'),
    ('under_review',    'Under Review'),
    ('returned',        'Returned'),
    ('rejected',        'Rejected'),
    ('approved',        'Approved'),
    ('to_pay',          'To Pay'),
    ('paid',            'Paid'),
    ('awaiting_report', 'Awaiting Report'),
    ('closed',          'Closed'),
]

TERMINAL_STATES = ['rejected', 'paid', 'closed']


class MinistrySupportRequest(models.Model):
    """Ministry of Sports financial support request.

    Manages the complete lifecycle from federation submission through
    multi-level ministerial approval to payment and post-event closure.
    Integrates with the calculation engine, risk scorer, Odoo Approvals,
    and Accounting modules.
    """
    _name = 'ministry.support.request'
    _description = 'Support Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'create_date desc'

    # ── Identity ─────────────────────────────────────────────────────────────
    name = fields.Char(
        string='Reference',
        readonly=True,
        copy=False,
        default='New',
        help='Auto-generated reference in format SR/YYYY/NNNNN.',
    )
    federation_id = fields.Many2one(
        'res.partner',
        string='Federation',
        required=True,
        domain="[('is_federation', '=', True)]",
        tracking=True,
        help='The federation submitting this request.',
    )
    support_item_id = fields.Many2one(
        'ministry.support.item',
        string='Support Item',
        required=True,
        tracking=True,
        help='The support catalog item this request is for.',
    )
    category = fields.Selection(
        related='support_item_id.category',
        store=True,
        string='Category',
        help='Support category derived from the selected item.',
    )
    fiscal_year = fields.Char(
        string='Fiscal Year',
        required=True,
        default=lambda self: self.env['ir.config_parameter'].sudo().get_param(
            'ministry.fiscal_year', '2026'
        ),
        help='The fiscal year this request applies to.',
    )
    state = fields.Selection(
        STATES,
        string='Status',
        default='draft',
        tracking=True,
        copy=False,
        help='Current lifecycle state of the request.',
    )

    # ── Amounts ───────────────────────────────────────────────────────────────
    requested_amount = fields.Float(
        string='Requested Amount (AED)',
        digits=(16, 2),
        tracking=True,
        help='Amount the federation is requesting from the Ministry.',
    )
    participants_count = fields.Integer(
        string='Participants / Count',
        default=1,
        help='Number of participants, referees, or events — used for by_count calc method.',
    )
    eligible_amount = fields.Float(
        string='Eligible Amount (AED)',
        digits=(16, 2),
        compute='_compute_eligible_amount',
        store=True,
        help='Amount calculated by the engine based on the item\'s calc method and limits.',
    )
    approved_amount = fields.Float(
        string='Approved Amount (AED)',
        digits=(16, 2),
        tracking=True,
        help='Amount approved by Ministry — may differ from eligible_amount.',
    )
    net_payable = fields.Float(
        string='Net Payable (AED)',
        digits=(16, 2),
        help='Approved amount after applying any pending deductions.',
    )
    variance_pct = fields.Float(
        string='YoY Variance (%)',
        digits=(5, 2),
        compute='_compute_variance_pct',
        store=True,
        help='Percentage change vs. same item in the previous fiscal year.',
    )
    requested_over_eligible = fields.Float(
        string='Requested Over Eligible (AED)',
        compute='_compute_decision_cockpit',
        store=True,
        help='Positive difference between requested and eligible amounts.',
    )
    requested_over_eligible_pct = fields.Float(
        string='Requested Over Eligible (%)',
        compute='_compute_decision_cockpit',
        store=True,
        help='Percentage of the requested amount that exceeds the calculated eligible amount.',
    )

    # ── Risk ──────────────────────────────────────────────────────────────────
    risk_score = fields.Float(
        string='Risk Score',
        digits=(5, 2),
        help='Composite risk score (0–100) for this specific request.',
    )
    risk_level = fields.Selection(
        [('low', 'Low'), ('medium', 'Medium'), ('high', 'High')],
        string='Risk Level',
        default='low',
        help='Risk classification derived from the risk score.',
    )
    decision_recommendation = fields.Selection(
        [
            ('approve', 'Approve'),
            ('approve_eligible', 'Approve Eligible Amount'),
            ('review', 'Needs Review'),
            ('return', 'Return for Clarification'),
            ('reject', 'Do Not Approve'),
        ],
        string='Decision Recommendation',
        compute='_compute_decision_cockpit',
        store=True,
        help='Decision support recommendation based on amount, eligibility, risk, and federation status.',
    )
    decision_attention_level = fields.Selection(
        [('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('blocked', 'Blocked')],
        string='Attention Level',
        compute='_compute_decision_cockpit',
        store=True,
        help='Operational priority for the reviewer.',
    )
    decision_blocked = fields.Boolean(
        string='Decision Blocked',
        compute='_compute_decision_cockpit',
        store=True,
    )
    decision_summary = fields.Text(
        string='Decision Summary',
        compute='_compute_decision_cockpit',
        store=True,
        help='Main decision reasons for the reviewer.',
    )
    federation_status = fields.Selection(
        related='federation_id.federation_status',
        string='Federation Status',
        readonly=True,
    )
    support_item_calc_method = fields.Selection(
        related='support_item_id.calc_method',
        string='Calculation Method',
        readonly=True,
    )
    support_item_max_limit = fields.Float(
        related='support_item_id.max_limit',
        string='Item Maximum Limit (AED)',
        readonly=True,
    )

    # ── Description & Context ────────────────────────────────────────────────
    description = fields.Text(
        string='Request Description',
        help='Detailed description of what the support will be used for.',
    )
    event_name = fields.Char(
        string='Event / Activity Name',
        help='Name of the specific event or activity being supported.',
    )
    event_date_start = fields.Date(string='Event Start Date')
    event_date_end = fields.Date(string='Event End Date')
    location = fields.Char(string='Location / Venue')

    # ── Attachments ──────────────────────────────────────────────────────────
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'support_request_attachment_rel',
        'request_id',
        'attachment_id',
        string='Attachments',
        help='Supporting documents: invitations, budgets, approvals, etc.',
    )
    attachment_count = fields.Integer(
        string='Supporting Document Count',
        compute='_compute_attachment_count',
    )

    # ── Review & Approval ────────────────────────────────────────────────────
    reviewed_by = fields.Many2one('res.users', string='Reviewed By', readonly=True)
    review_date = fields.Date(string='Review Date', readonly=True)
    approved_by = fields.Many2one('res.users', string='Approved By', readonly=True)
    approval_date = fields.Date(string='Approval Date', readonly=True)
    return_reason = fields.Text(string='Return / Rejection Reason', tracking=True)

    # ── Financial Integration ─────────────────────────────────────────────────
    vendor_bill_id = fields.Many2one(
        'account.move',
        string='Vendor Bill',
        readonly=True,
        copy=False,
        help='Auto-created vendor bill when the request is approved.',
    )

    # ── Multi-company ─────────────────────────────────────────────────────────
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        store=True,
    )

    # ── Compute Methods ───────────────────────────────────────────────────────

    @api.depends('support_item_id', 'requested_amount', 'participants_count', 'state')
    def _compute_eligible_amount(self):
        """Compute eligible amount via the calculation engine."""
        engine = self.env['ministry.calc.engine']
        for req in self:
            if req.support_item_id and req.state == 'draft':
                req.eligible_amount = engine.compute_eligible_amount(req)
            elif not req.eligible_amount:
                req.eligible_amount = 0.0

    @api.depends('support_item_id', 'fiscal_year', 'federation_id', 'eligible_amount')
    def _compute_variance_pct(self):
        """Compute YoY variance via the calculation engine."""
        engine = self.env['ministry.calc.engine']
        for req in self:
            if req.federation_id and req.support_item_id and req.fiscal_year:
                req.variance_pct = engine.compute_variance(req)
            else:
                req.variance_pct = 0.0

    def _compute_attachment_count(self):
        for req in self:
            req.attachment_count = len(req.attachment_ids)

    @api.depends(
        'requested_amount', 'eligible_amount', 'approved_amount', 'variance_pct',
        'risk_level', 'federation_id.federation_status', 'support_item_id',
        'attachment_ids', 'state',
    )
    def _compute_decision_cockpit(self):
        for req in self:
            gap = max((req.requested_amount or 0.0) - (req.eligible_amount or 0.0), 0.0)
            req.requested_over_eligible = gap
            req.requested_over_eligible_pct = (
                round((gap / req.requested_amount) * 100.0, 2)
                if req.requested_amount else 0.0
            )

            reasons = []
            recommendation = 'approve'
            attention = 'low'
            blocked = False

            if not req.federation_id or not req.support_item_id:
                recommendation = 'review'
                attention = 'medium'
                reasons.append(_('Select a federation and support item to complete the decision check.'))
            elif req.federation_status == 'suspended':
                recommendation = 'reject'
                attention = 'blocked'
                blocked = True
                reasons.append(_('Federation is suspended; support should not be approved until suspension is lifted.'))
            elif req.requested_amount and req.eligible_amount <= 0:
                recommendation = 'return'
                attention = 'high'
                blocked = True
                reasons.append(_('Eligibility calculation returned AED 0.00. Review the support item rule or return the request for correction.'))

            if not blocked and gap:
                recommendation = 'approve_eligible'
                attention = 'medium'
                reasons.append(_(
                    'Requested amount exceeds eligible amount by AED %(gap)s (%(pct)s%%).',
                    gap='{:,.2f}'.format(gap),
                    pct='{:,.2f}'.format(req.requested_over_eligible_pct),
                ))

            if not blocked and req.risk_level == 'high':
                recommendation = 'review'
                attention = 'high'
                reasons.append(_('Request is high risk and should receive management review before approval.'))
            elif not blocked and req.risk_level == 'medium' and attention == 'low':
                attention = 'medium'
                reasons.append(_('Request has medium risk indicators.'))

            if not blocked and abs(req.variance_pct or 0.0) > 30:
                recommendation = 'review'
                attention = 'high'
                reasons.append(_(
                    'Year-over-year variance is %(variance)s%%, above the 30%% review threshold.',
                    variance='{:,.2f}'.format(req.variance_pct),
                ))

            if not blocked and req.state in ('submitted', 'under_review') and not req.attachment_count:
                recommendation = 'return'
                attention = 'high'
                reasons.append(_('No supporting documents are attached.'))

            if not reasons:
                reasons.append(_('Request is within current eligibility, risk, and amount thresholds.'))

            req.decision_recommendation = recommendation
            req.decision_attention_level = attention
            req.decision_blocked = blocked
            req.decision_summary = '\n'.join(reasons)

    # ── Lifecycle Actions ─────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-assign sequence reference on creation."""
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('ministry.support.request') or 'New'
        return super().create(vals_list)

    def action_submit(self):
        """Submit the request to the Ministry for review.

        Workflow:
            1. Validate required attachments are present.
            2. Re-compute eligible amount and risk score.
            3. Set state to 'submitted'.
            4. Post chatter message.
        """
        for req in self:
            if req.state != 'draft':
                raise UserError('Only draft requests can be submitted.')
            if not req.requested_amount:
                raise UserError('Please enter the requested amount before submitting.')

            # Recompute on submit
            engine = self.env['ministry.calc.engine']
            req.eligible_amount = engine.compute_eligible_amount(req)
            req.variance_pct = engine.compute_variance(req)

            scorer = self.env['ministry.risk.scorer']
            risk = scorer.score_request(req)
            req.risk_score = risk['risk_score']
            req.risk_level = risk['risk_level']

            req.write({'state': 'submitted'})
            req.message_post(body=_(
                'Request %(ref)s submitted for Ministry review. '
                'Eligible: %(eligible)s AED | Risk: %(level)s (%(score)s%%)',
                ref=req.name,
                eligible='{:,.2f}'.format(req.eligible_amount),
                level=req.risk_level,
                score='{:.1f}'.format(req.risk_score),
            ))

    def action_review(self):
        """Move request to Under Review state."""
        for req in self:
            if req.state not in ('submitted', 'returned'):
                raise UserError('Request must be submitted or returned before review.')
            req.write({
                'state': 'under_review',
                'reviewed_by': self.env.user.id,
                'review_date': fields.Date.today(),
            })
            req.message_post(body=_(
                'Request taken under review by %(user)s.',
                user=self.env.user.name,
            ))

    def action_approve(self):
        """Approve the request and auto-create the vendor bill.

        Workflow:
            1. Validate approved_amount is set.
            2. Apply pending deductions to compute net_payable.
            3. Create vendor bill in draft state.
            4. Set state to 'approved'.
        """
        for req in self:
            if req.state not in ('under_review',):
                raise UserError('Only requests under review can be approved.')
            if not req.approved_amount:
                req.approved_amount = req.eligible_amount
            if not req.approved_amount:
                raise UserError('Set an approved amount before approving.')

            engine = self.env['ministry.calc.engine']
            req.net_payable = engine.apply_pending_deductions(req, req.approved_amount)

            bill = req._create_vendor_bill()
            req.write({
                'state': 'approved',
                'vendor_bill_id': bill.id,
                'approved_by': self.env.user.id,
                'approval_date': fields.Date.today(),
            })
            req.message_post(body=_(
                'Request approved by %(user)s. '
                'Approved: %(amount)s AED | Net payable: %(net)s AED. '
                'Vendor bill %(bill)s created.',
                user=self.env.user.name,
                amount='{:,.2f}'.format(req.approved_amount),
                net='{:,.2f}'.format(req.net_payable),
                bill=bill.name,
            ))

    def action_register_payment(self):
        """Trigger the standard Odoo payment wizard on the linked vendor bill."""
        self.ensure_one()
        if self.state not in ('approved', 'to_pay'):
            raise UserError('Only approved requests can be sent to payment.')
        if not self.vendor_bill_id:
            raise UserError('No vendor bill linked to this request.')
        if self.state == 'approved':
            self.write({'state': 'to_pay'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment.register',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {
                'active_model': 'account.move',
                'active_ids': [self.vendor_bill_id.id],
            },
        }

    def action_mark_paid(self):
        """Mark request as paid after payment is confirmed."""
        for req in self:
            req.write({'state': 'paid'})
            # Activity requests that required a post-event report
            if req.category == 'activity':
                req.write({'state': 'awaiting_report'})
                req.message_post(body=_(
                    'Payment confirmed. Request moved to Awaiting Post-Event Report.'
                ))
            else:
                req.message_post(body=_('Payment confirmed. Request closed.'))

    def action_mark_awaiting_report(self):
        """Move activity requests to Awaiting Report state after payment."""
        for req in self:
            req.write({'state': 'awaiting_report'})
            req.message_post(body=_(
                'Request awaiting post-event report. '
                'Federation must submit within 15 days of event completion.'
            ))

    def action_close(self):
        """Close the request after post-event report is received."""
        for req in self:
            if req.state not in ('awaiting_report', 'paid'):
                raise UserError('Only paid or awaiting-report requests can be closed.')
            req.write({'state': 'closed'})
            req.message_post(body=_('Request closed successfully.'))

    def action_return(self):
        """Return the request to the federation for revision."""
        self.ensure_one()
        if self.state not in ('submitted', 'under_review'):
            raise UserError('Only submitted or under-review requests can be returned.')
        if not self.return_reason:
            raise UserError('Please provide a return reason before returning the request.')
        self.write({'state': 'returned'})
        self.message_post(body=_(
            'Request returned to federation. Reason: %(reason)s',
            reason=self.return_reason,
        ))

    def action_reject(self):
        """Reject the request — terminal state."""
        for req in self:
            if req.state not in ('submitted', 'under_review', 'returned'):
                raise UserError('Only submitted, under-review, or returned requests can be rejected.')
            if not req.return_reason:
                raise UserError('Please provide a rejection reason before rejecting.')
            req.write({'state': 'rejected'})
            req.message_post(body=_(
                'Request rejected. Reason: %(reason)s',
                reason=req.return_reason,
            ))

    def action_reset_to_draft(self):
        """Reset returned request back to draft for federation editing."""
        for req in self:
            if req.state not in ('returned', 'draft'):
                raise UserError('Only returned requests can be reset to draft.')
            req.write({'state': 'draft'})

    def action_set_approved_to_eligible(self):
        """Set the approved amount to the calculated eligible amount."""
        for req in self:
            if req.state not in ('draft', 'submitted', 'under_review', 'returned'):
                raise UserError('Approved amount can only be adjusted before approval.')
            if not req.eligible_amount:
                raise UserError('Eligible amount is zero. Recalculate or review the support item rule first.')
            req.approved_amount = req.eligible_amount
            req.message_post(body=_(
                'Approved amount set to eligible amount: %(amount)s AED.',
                amount='{:,.2f}'.format(req.eligible_amount),
            ))

    def action_recalculate_decision(self):
        """Refresh eligibility, variance, risk score, and decision cockpit values."""
        engine = self.env['ministry.calc.engine']
        scorer = self.env['ministry.risk.scorer']
        for req in self:
            if not req.support_item_id:
                raise UserError('Select a support item before recalculating.')
            req.eligible_amount = engine.compute_eligible_amount(req)
            req.variance_pct = engine.compute_variance(req)
            if req.federation_id:
                risk = scorer.score_request(req)
                req.risk_score = risk['risk_score']
                req.risk_level = risk['risk_level']
            req.message_post(body=_(
                'Decision check recalculated. Eligible: %(eligible)s AED | Risk: %(risk)s.',
                eligible='{:,.2f}'.format(req.eligible_amount),
                risk=req.risk_level or '-',
            ))

    # ── Private Helpers ───────────────────────────────────────────────────────

    def _create_vendor_bill(self):
        """Create a draft vendor bill for the approved amount.

        Returns:
            account.move: Newly created draft vendor bill record.
        """
        self.ensure_one()
        journal = self.env['account.journal'].search([
            ('type', '=', 'purchase'),
            ('company_id', '=', self.company_id.id),
        ], limit=1)
        if not journal:
            raise UserError('No purchase journal found. Please configure the accounting setup.')

        bill_vals = {
            'move_type': 'in_invoice',
            'partner_id': self.federation_id.id,
            'journal_id': journal.id,
            'ref': self.name,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, {
                'name': f'{self.support_item_id.name} — {self.name}',
                'quantity': 1.0,
                'price_unit': self.net_payable or self.approved_amount,
                'analytic_distribution': self._get_analytic_distribution(),
            })],
        }
        return self.env['account.move'].create(bill_vals)

    def _get_analytic_distribution(self):
        """Build the analytic distribution used by Odoo Budget reporting."""
        accounts_by_plan = {}
        for account in self._get_ministry_analytic_accounts():
            accounts_by_plan[account.plan_id.root_id.id] = account
        if self.support_item_id.analytic_account_id:
            account = self.support_item_id.analytic_account_id
            accounts_by_plan.setdefault(account.plan_id.root_id.id, account)
        account_ids = sorted(account.id for account in accounts_by_plan.values())
        return {','.join(str(account_id) for account_id in account_ids): 100.0} if account_ids else {}

    def _get_ministry_analytic_accounts(self):
        accounts = self.env['account.analytic.account']
        accounts |= self._get_or_create_analytic_account(
            'Federation',
            self._clean_federation_name(self.federation_id.display_name),
            self._federation_analytic_code(),
        )
        if self.category:
            category_label, category_code = self._category_analytic_values(self.category)
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

    def action_open_vendor_bill(self):
        self.ensure_one()
        if not self.vendor_bill_id:
            raise UserError('No vendor bill linked.')
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.vendor_bill_id.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
        }

    def action_get_attachment_view(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Documents'),
            'res_model': 'ir.attachment',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [('id', 'in', self.attachment_ids.ids)],
            'context': {
                'default_res_model': self._name,
                'default_res_id': self.id,
            },
        }
