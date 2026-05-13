# -*- coding: utf-8 -*-
import logging
from odoo import _, fields, models
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)

# Sentinel for "no result from safe_eval expression"
_MISSING = object()


class MinistryCalcEngine(models.AbstractModel):
    """Stateless calculation service for support request amounts.

    All methods operate on a support request recordset (single record expected).
    Instantiate by calling self.env['ministry.calc.engine'] from any model.
    """
    _name = 'ministry.calc.engine'
    _description = 'Ministry Calculation Engine'

    def compute_eligible_amount(self, request):
        """Compute the eligible amount for a support request.

        Applies calc_method logic, max_limit cap, and eligibility expression.

        Workflow:
            1. Determine base amount from calc_method (fixed / by_count / by_request).
            2. Evaluate eligibility_python — return 0.0 if not eligible.
            3. Apply max_limit cap (if max_limit > 0).
            4. Post a chatter note if the amount was capped.

        Args:
            request: Single ministry.support.request record.

        Returns:
            float: Eligible amount in AED (0.0 if ineligible).
        """
        item = request.support_item_id
        if not item:
            return 0.0

        # Step 1 — Base amount
        base_amount = self._apply_calc_method(request, item)

        # Step 2 — Eligibility check
        if item.eligibility_python:
            is_eligible = self._evaluate_eligibility(request, item)
            if not is_eligible:
                _logger.info(
                    'CalcEngine: request %s ineligible by python expression for item %s',
                    request.name, item.code,
                )
                return 0.0

        # Step 3 — Apply max_limit cap
        if item.max_limit > 0 and base_amount > item.max_limit:
            _logger.info(
                'CalcEngine: request %s capped from %.2f to %.2f (max_limit)',
                request.name, base_amount, item.max_limit,
            )
            request.message_post(body=_(
                'Eligible amount capped at %(limit)s AED (max limit for %(item)s). '
                'Original calculated: %(orig)s AED.',
                limit='{:,.2f}'.format(item.max_limit),
                item=item.name,
                orig='{:,.2f}'.format(base_amount),
            ))
            return item.max_limit

        return base_amount

    def compute_variance(self, request):
        """Compute year-over-year variance percent vs. previous fiscal year.

        Compares the current request's eligible amount against the average
        approved amount for the same federation + item in the prior fiscal year.

        Args:
            request: Single ministry.support.request record.

        Returns:
            float: Variance as a percentage (positive = increase, negative = decrease).
                   Returns 0.0 if no prior-year data exists.
        """
        prior_year = str(int(request.fiscal_year) - 1) if request.fiscal_year else None
        if not prior_year:
            return 0.0

        prior_requests = self.env['ministry.support.request'].search([
            ('federation_id', '=', request.federation_id.id),
            ('support_item_id', '=', request.support_item_id.id),
            ('fiscal_year', '=', prior_year),
            ('state', 'in', ['approved', 'to_pay', 'paid', 'awaiting_report', 'closed']),
        ])

        if not prior_requests:
            return 0.0

        prior_avg = sum(prior_requests.mapped('approved_amount')) / len(prior_requests)
        if prior_avg == 0:
            return 0.0

        current_eligible = request.eligible_amount or self.compute_eligible_amount(request)
        variance = ((current_eligible - prior_avg) / prior_avg) * 100.0
        return round(variance, 2)

    def apply_pending_deductions(self, request, amount):
        """Consume pending deductions queued for the federation.

        Deductions are created by legal actions and applied in FIFO order
        until exhausted or the payment amount is fully consumed.

        Workflow:
            1. Fetch all pending deductions for the federation, ordered by creation date.
            2. Subtract each deduction from amount (minimum 0.0 result).
            3. Mark each fully-consumed deduction as applied.
            4. Post a chatter note per deduction applied.

        Args:
            request: Single ministry.support.request record.
            amount: Float — the approved amount before deductions (AED).

        Returns:
            float: Net payable amount after all deductions applied.
        """
        deductions = self.env['ministry.pending.deduction'].search([
            ('federation_id', '=', request.federation_id.id),
            ('state', '=', 'pending'),
        ], order='create_date asc')

        remaining = amount
        for ded in deductions:
            if remaining <= 0:
                break
            applied = min(ded.deduction_amount, remaining)
            remaining -= applied
            ded.write({
                'state': 'applied',
                'applied_on_request_id': request.id,
                'applied_date': fields.Date.today(),
            })
            request.message_post(body=_(
                'Deduction of %(amount)s AED applied from legal action %(ref)s. '
                'Remaining payable: %(remaining)s AED.',
                amount='{:,.2f}'.format(applied),
                ref=ded.legal_action_id.name if ded.legal_action_id else 'N/A',
                remaining='{:,.2f}'.format(remaining),
            ))

        return max(remaining, 0.0)

    # ── Private helpers ──────────────────────────────────────────────────────

    def _apply_calc_method(self, request, item):
        """Return base amount based on the item's calculation method.

        Args:
            request: ministry.support.request record.
            item: ministry.support.item record.

        Returns:
            float: Raw calculated amount before cap and eligibility check.
        """
        if item.calc_method == 'fixed_amount':
            return item.fixed_amount
        if item.calc_method == 'by_count':
            return item.unit_amount * (request.participants_count or 1)
        if item.calc_method == 'by_request':
            return request.requested_amount
        return 0.0

    def _evaluate_eligibility(self, request, item):
        """Safely evaluate the item's eligibility_python expression.

        Args:
            request: ministry.support.request record.
            item: ministry.support.item record.

        Returns:
            bool: True if eligible, False otherwise. Defaults to True on error.
        """
        context = {
            'federation': request.federation_id,
            'request': request,
            'item': item,
            'result': True,
        }
        try:
            safe_eval(item.eligibility_python, context, mode='exec')
            return bool(context.get('result', True))
        except Exception as exc:
            _logger.warning(
                'CalcEngine: eligibility expression error for item %s: %s',
                item.code, exc,
            )
            return True
