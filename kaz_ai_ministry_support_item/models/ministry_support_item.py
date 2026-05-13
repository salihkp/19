# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class MinistrySupportItem(models.Model):
    _name = 'ministry.support.item'
    _description = 'Support Item'
    _inherit = ['mail.thread']
    _rec_name = 'name'
    _order = 'category, sequence, name'

    name = fields.Char(
        string='Item Name',
        required=True,
        tracking=True,
        help='Official name of this support item as it appears in requests and reports.',
    )
    code = fields.Char(
        string='Code',
        required=True,
        help='Unique short code used in sequences and calculation references (e.g., OP-SAL-01).',
    )
    sequence = fields.Integer(default=10)
    category = fields.Selection(
        [
            ('operational', 'Operational Support'),
            ('technical', 'Technical Support'),
            ('general', 'General Financial Support'),
            ('activity', 'Activity Support'),
        ],
        string='Category',
        required=True,
        tracking=True,
        help='The broad support category this item falls under.',
    )
    group_id = fields.Many2one(
        'ministry.support.group',
        string='Group',
        help='Sub-group within the category for reporting purposes.',
    )
    item_type = fields.Selection(
        [('fixed', 'Fixed'), ('variable', 'Variable')],
        string='Item Type',
        required=True,
        default='fixed',
        help='Fixed: amount is predetermined. Variable: amount depends on count or request.',
    )
    calc_method = fields.Selection(
        [
            ('fixed_amount', 'Fixed Amount'),
            ('by_count', 'Per Unit / Count'),
            ('by_request', 'Per Request (Requested Amount)'),
        ],
        string='Calculation Method',
        required=True,
        default='fixed_amount',
        tracking=True,
        help='How the eligible amount is calculated:\n'
             '- Fixed Amount: uses the fixed_amount field directly\n'
             '- Per Unit / Count: unit_amount × participants_count\n'
             '- Per Request: uses the amount the federation requests (subject to max_limit)',
    )
    fixed_amount = fields.Float(
        string='Fixed Amount (AED)',
        digits=(16, 2),
        help='The fixed AED amount applied when calc_method is "fixed_amount".',
    )
    unit_amount = fields.Float(
        string='Unit Amount (AED)',
        digits=(16, 2),
        help='Amount per unit (person, referee, event) when calc_method is "by_count".',
    )
    max_limit = fields.Float(
        string='Maximum Limit (AED)',
        digits=(16, 2),
        help='Hard ceiling for the eligible amount. 0 means no cap.',
    )
    eligibility_python = fields.Text(
        string='Eligibility Expression',
        help='Python expression evaluated by safe_eval. Variables available: federation, request, item.\n'
             'Set result = True or result = False. Leave empty to always allow.',
    )
    calculation_summary = fields.Text(
        string='Calculation Summary',
        compute='_compute_decision_summaries',
        store=True,
        help='Plain-language explanation of how the eligible amount is calculated.',
    )
    eligibility_rule_summary = fields.Text(
        string='Eligibility Rule Summary',
        compute='_compute_decision_summaries',
        store=True,
        help='Plain-language explanation of the eligibility rule used by the calculation engine.',
    )
    has_eligibility_rule = fields.Boolean(
        string='Has Eligibility Rule',
        compute='_compute_decision_summaries',
        store=True,
    )
    required_attachment_count = fields.Integer(
        string='Required Documents',
        compute='_compute_required_attachment_count',
        store=True,
    )
    required_attachment_types_ids = fields.Many2many(
        'ministry.attachment.type',
        'support_item_attachment_type_rel',
        'item_id',
        'attachment_type_id',
        string='Required Attachments',
        help='Attachment types the federation must upload to submit a request for this item.',
    )
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        help='Analytic account to tag on the vendor bill line when this item is approved.',
    )
    active = fields.Boolean(default=True,
        help='Uncheck to archive this item without removing it from historical requests.')
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
    )

    _code_company_uniq = models.Constraint(
        'UNIQUE(code, company_id)',
        'Support item code must be unique per company.',
    )

    @api.depends('calc_method', 'fixed_amount', 'unit_amount', 'max_limit', 'eligibility_python')
    def _compute_decision_summaries(self):
        method_labels = dict(self._fields['calc_method'].selection)
        for item in self:
            cap = (
                _(' capped at AED %(amount)s', amount='{:,.2f}'.format(item.max_limit))
                if item.max_limit else _(' with no configured cap')
            )
            if item.calc_method == 'fixed_amount':
                item.calculation_summary = _(
                    'Eligible amount uses the fixed support value of AED %(amount)s%(cap)s.',
                    amount='{:,.2f}'.format(item.fixed_amount),
                    cap=cap,
                )
            elif item.calc_method == 'by_count':
                item.calculation_summary = _(
                    'Eligible amount is AED %(unit)s multiplied by the request count%(cap)s.',
                    unit='{:,.2f}'.format(item.unit_amount),
                    cap=cap,
                )
            elif item.calc_method == 'by_request':
                item.calculation_summary = _(
                    'Eligible amount starts from the requested amount%(cap)s.',
                    cap=cap,
                )
            else:
                item.calculation_summary = _(
                    'Calculation method: %(method)s.',
                    method=method_labels.get(item.calc_method, item.calc_method or '-'),
                )

            item.has_eligibility_rule = bool(item.eligibility_python)
            if item.has_eligibility_rule:
                item.eligibility_rule_summary = _(
                    'Rule active. The engine evaluates federation, request, and item data; '
                    'the rule must set result = True or result = False. Current rule: %(rule)s',
                    rule=item.eligibility_python.strip(),
                )
            else:
                item.eligibility_rule_summary = _(
                    'No additional eligibility expression. The item is eligible unless another workflow control blocks it.'
                )

    @api.depends('required_attachment_types_ids')
    def _compute_required_attachment_count(self):
        for item in self:
            item.required_attachment_count = len(item.required_attachment_types_ids)

    @api.constrains('calc_method', 'fixed_amount', 'unit_amount')
    def _check_amounts(self):
        """Ensure the correct amount field is set for the chosen calculation method."""
        for item in self:
            if item.calc_method == 'fixed_amount' and item.fixed_amount <= 0:
                raise ValidationError(
                    f'Item "{item.name}": Fixed amount must be greater than 0.'
                )
            if item.calc_method == 'by_count' and item.unit_amount <= 0:
                raise ValidationError(
                    f'Item "{item.name}": Unit amount must be greater than 0 for per-count calculation.'
                )

    @api.constrains('max_limit')
    def _check_max_limit(self):
        for item in self:
            if item.max_limit < 0:
                raise ValidationError(_('Maximum limit cannot be negative.'))
