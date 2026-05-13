# -*- coding: utf-8 -*-
from odoo import api, models, _
import logging

_logger = logging.getLogger(__name__)


class MinistryAnalyticsService(models.AbstractModel):
    """Analytics service: anomaly detection, forecasting, and burn rate calculation.

    All public methods return structured dicts consumed by the dashboard JSON-RPC
    endpoint and the nightly scheduled action.
    """
    _name = 'ministry.analytics.service'
    _description = 'Ministry Analytics Service'

    # ── Public API ───────────────────────────────────────────────────────────

    def run_nightly_analysis(self):
        """Entry point called by the scheduled action.

        Workflow:
            1. Detect abnormal budget increases across all federations.
            2. Calculate current-year budget burn rate.
            3. Forecast next-quarter spend.
            4. Create ministry.analytics.alert records for any findings.
        """
        self._run_abnormal_increase_check()
        self._run_burn_rate_check()

    def get_dashboard_data(self):
        """Return a dict of KPI data for the OWL dashboard.

        Workflow:
            1. Compute budget summary (total / spent / remaining).
            2. Compute request counts by state.
            3. Build chart datasets for bar and donut charts.
            4. Build 12-month trend line.

        Returns:
            dict: Structured data ready for JSON serialisation.
        """
        return {
            'budget': self._budget_summary(),
            'requests': self._request_counts(),
            'federation_breakdown': self._federation_breakdown(),
            'category_breakdown': self._category_breakdown(),
            'monthly_trend': self._monthly_trend(),
            'risk_summary': self._risk_summary(),
        }

    def detect_abnormal_increases(self, threshold_pct=30.0):
        """Detect federations with year-on-year approved amount increases above threshold.

        Args:
            threshold_pct: Percentage variance above which an increase is flagged.

        Returns:
            list[dict]: Each dict has federation_id, federation_name, current_year,
                        prior_year, variance_pct.
        """
        Request = self.env['ministry.support.request']
        current_year = str(self.env['ir.config_parameter'].sudo().get_param('ministry.fiscal_year', '2026'))
        prior_year = str(int(current_year) - 1)

        results = []
        federations = self.env['res.partner'].search([('is_federation', '=', True)])
        for fed in federations:
            current = sum(Request.search([
                ('federation_id', '=', fed.id),
                ('fiscal_year', '=', current_year),
                ('state', 'in', ['approved', 'paid', 'closed']),
            ]).mapped('approved_amount'))
            prior = sum(Request.search([
                ('federation_id', '=', fed.id),
                ('fiscal_year', '=', prior_year),
                ('state', 'in', ['approved', 'paid', 'closed']),
            ]).mapped('approved_amount'))

            if prior > 0:
                variance = ((current - prior) / prior) * 100
                if abs(variance) >= threshold_pct:
                    results.append({
                        'federation_id': fed.id,
                        'federation_name': fed.name,
                        'current_year_amount': current,
                        'prior_year_amount': prior,
                        'variance_pct': round(variance, 2),
                    })
        return results

    def forecast_next_quarter(self):
        """Simple linear extrapolation of approved spend for the next quarter.

        Returns:
            dict: Mapping month_label → forecasted_amount for the next 3 months.
        """
        from datetime import date
        from dateutil.relativedelta import relativedelta

        Request = self.env['ministry.support.request']
        today = date.today()
        monthly_totals = {}

        for offset in range(6, 0, -1):
            month_start = (today - relativedelta(months=offset)).replace(day=1)
            month_end = (month_start + relativedelta(months=1, days=-1))
            total = sum(Request.search([
                ('state', 'in', ['approved', 'paid', 'closed']),
                ('approval_date', '>=', month_start.strftime('%Y-%m-%d')),
                ('approval_date', '<=', month_end.strftime('%Y-%m-%d')),
            ]).mapped('approved_amount'))
            monthly_totals[month_start.strftime('%b %Y')] = total

        avg_monthly = sum(monthly_totals.values()) / max(len(monthly_totals), 1)
        forecast = {}
        for i in range(1, 4):
            future_month = (today + relativedelta(months=i)).replace(day=1)
            forecast[future_month.strftime('%b %Y')] = round(avg_monthly, 2)

        return forecast

    def budget_burn_rate(self):
        """Calculate current-year budget utilisation rate.

        Returns:
            dict: annual_budget, total_approved, burn_rate_pct, remaining.
        """
        return self._budget_summary()

    def federation_behavior_summary(self):
        """Return per-federation summary for analyst reporting.

        Returns:
            list[dict]: One entry per federation with key metrics.
        """
        Request = self.env['ministry.support.request']
        current_year = str(self.env['ir.config_parameter'].sudo().get_param('ministry.fiscal_year', '2026'))
        federations = self.env['res.partner'].search([('is_federation', '=', True)])
        summary = []

        for fed in federations:
            requests = Request.search([
                ('federation_id', '=', fed.id),
                ('fiscal_year', '=', current_year),
            ])
            total_requested = sum(requests.mapped('requested_amount'))
            total_approved = sum(requests.mapped('approved_amount'))
            approval_rate = (total_approved / total_requested * 100) if total_requested > 0 else 0
            summary.append({
                'federation': fed.name,
                'risk_level': fed.risk_level,
                'risk_score': fed.risk_score,
                'total_requests': len(requests),
                'total_requested': total_requested,
                'total_approved': total_approved,
                'approval_rate_pct': round(approval_rate, 1),
            })
        return summary

    # ── Private helpers ──────────────────────────────────────────────────────

    def _budget_summary(self):
        """Return total annual budget, approved spend, and remaining balance."""
        Param = self.env['ir.config_parameter'].sudo()
        annual_budget = float(Param.get_param('ministry.annual_budget', '50000000'))
        current_year = Param.get_param('ministry.fiscal_year', '2026')

        total_approved = sum(self.env['ministry.support.request'].search([
            ('fiscal_year', '=', current_year),
            ('state', 'in', ['approved', 'to_pay', 'paid', 'awaiting_report', 'closed']),
        ]).mapped('approved_amount'))

        burn_rate = (total_approved / annual_budget * 100) if annual_budget > 0 else 0
        return {
            'annual_budget': annual_budget,
            'total_approved': total_approved,
            'remaining': annual_budget - total_approved,
            'burn_rate_pct': round(burn_rate, 1),
        }

    def _request_counts(self):
        """Return request counts by state group."""
        Request = self.env['ministry.support.request']
        current_year = self.env['ir.config_parameter'].sudo().get_param('ministry.fiscal_year', '2026')
        base = [('fiscal_year', '=', current_year)]
        return {
            'total': Request.search_count(base),
            'pending_review': Request.search_count(base + [('state', 'in', ['submitted', 'under_review'])]),
            'approved': Request.search_count(base + [('state', 'in', ['approved', 'to_pay'])]),
            'paid': Request.search_count(base + [('state', 'in', ['paid', 'closed'])]),
            'awaiting_report': Request.search_count(base + [('state', '=', 'awaiting_report')]),
            'rejected': Request.search_count(base + [('state', '=', 'rejected')]),
        }

    def _federation_breakdown(self):
        """Return approved amount per federation for bar chart."""
        Request = self.env['ministry.support.request']
        current_year = self.env['ir.config_parameter'].sudo().get_param('ministry.fiscal_year', '2026')
        federations = self.env['res.partner'].search([('is_federation', '=', True)])
        labels, data = [], []
        for fed in federations:
            total = sum(Request.search([
                ('federation_id', '=', fed.id),
                ('fiscal_year', '=', current_year),
                ('state', 'in', ['approved', 'to_pay', 'paid', 'awaiting_report', 'closed']),
            ]).mapped('approved_amount'))
            labels.append(fed.name)
            data.append(total)
        return {'labels': labels, 'data': data}

    def _category_breakdown(self):
        """Return approved amount per category for donut chart."""
        Request = self.env['ministry.support.request']
        current_year = self.env['ir.config_parameter'].sudo().get_param('ministry.fiscal_year', '2026')
        categories = [('operational', 'Operational'), ('technical', 'Technical'),
                      ('general', 'General'), ('activity', 'Activity')]
        labels, data = [], []
        for cat_key, cat_label in categories:
            total = sum(Request.search([
                ('category', '=', cat_key),
                ('fiscal_year', '=', current_year),
                ('state', 'in', ['approved', 'to_pay', 'paid', 'awaiting_report', 'closed']),
            ]).mapped('approved_amount'))
            labels.append(cat_label)
            data.append(total)
        return {'labels': labels, 'data': data}

    def _monthly_trend(self):
        """Return approved amounts for the last 12 months."""
        from datetime import date
        from dateutil.relativedelta import relativedelta

        Request = self.env['ministry.support.request']
        today = date.today()
        labels, data = [], []

        for offset in range(11, -1, -1):
            month_start = (today - relativedelta(months=offset)).replace(day=1)
            month_end = (month_start + relativedelta(months=1, days=-1))
            total = sum(Request.search([
                ('state', 'in', ['approved', 'to_pay', 'paid', 'awaiting_report', 'closed']),
                ('approval_date', '>=', month_start.strftime('%Y-%m-%d')),
                ('approval_date', '<=', month_end.strftime('%Y-%m-%d')),
            ]).mapped('approved_amount'))
            labels.append(month_start.strftime('%b %Y'))
            data.append(total)

        return {'labels': labels, 'data': data}

    def _risk_summary(self):
        """Return count of federations per risk level."""
        Partner = self.env['res.partner']
        return {
            'low': Partner.search_count([('is_federation', '=', True), ('risk_level', '=', 'low')]),
            'medium': Partner.search_count([('is_federation', '=', True), ('risk_level', '=', 'medium')]),
            'high': Partner.search_count([('is_federation', '=', True), ('risk_level', '=', 'high')]),
        }

    def _run_abnormal_increase_check(self):
        """Detect and log abnormal budget increases as analytics alerts."""
        findings = self.detect_abnormal_increases(threshold_pct=30.0)
        Alert = self.env['ministry.analytics.alert']
        for f in findings:
            existing = Alert.search([
                ('alert_type', '=', 'abnormal_increase'),
                ('federation_id', '=', f['federation_id']),
                ('is_acknowledged', '=', False),
            ], limit=1)
            if not existing:
                Alert.create({
                    'name': _('Abnormal budget increase: %(fed)s (+%(pct)s%%)',
                               fed=f['federation_name'],
                               pct=f['variance_pct']),
                    'alert_type': 'abnormal_increase',
                    'severity': 'critical' if f['variance_pct'] > 50 else 'warning',
                    'federation_id': f['federation_id'],
                    'detail': _(
                        'Current year approved: %(curr)s AED. Prior year: %(prior)s AED. Variance: %(pct)s%%.',
                        curr=f'{f["current_year_amount"]:,.2f}',
                        prior=f'{f["prior_year_amount"]:,.2f}',
                        pct=f['variance_pct'],
                    ),
                })

    def _run_burn_rate_check(self):
        """Log an alert if budget burn rate exceeds 80%."""
        summary = self._budget_summary()
        if summary['burn_rate_pct'] >= 80:
            Alert = self.env['ministry.analytics.alert']
            existing = Alert.search([
                ('alert_type', '=', 'high_burn_rate'),
                ('is_acknowledged', '=', False),
            ], limit=1)
            if not existing:
                Alert.create({
                    'name': _('High budget burn rate: %(pct)s%%', pct=summary['burn_rate_pct']),
                    'alert_type': 'high_burn_rate',
                    'severity': 'critical' if summary['burn_rate_pct'] >= 95 else 'warning',
                    'detail': _(
                        'Annual budget: %(budget)s AED. Approved to date: %(approved)s AED. Remaining: %(rem)s AED.',
                        budget=f'{summary["annual_budget"]:,.2f}',
                        approved=f'{summary["total_approved"]:,.2f}',
                        rem=f'{summary["remaining"]:,.2f}',
                    ),
                })
