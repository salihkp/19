# -*- coding: utf-8 -*-
import logging
from datetime import date, timedelta
from odoo import models

_logger = logging.getLogger(__name__)

_LEVEL_LOW = 35.0
_LEVEL_HIGH = 65.0


class MinistryRiskScorer(models.AbstractModel):
    """Multi-dimensional risk scoring service for federations and requests.

    Computes a composite score (0–100) across five weighted dimensions.
    Weights are read from ir.config_parameter and default to the design spec values.
    """
    _name = 'ministry.risk.scorer'
    _description = 'Ministry Risk Scoring Engine'

    # ── Public API ───────────────────────────────────────────────────────────

    def score_federation(self, federation):
        """Compute and persist risk score for a federation partner record.

        Workflow:
            1. Read configurable weights from system parameters.
            2. Compute each dimension score (0–100 per dimension).
            3. Calculate weighted composite score.
            4. Determine risk level from thresholds.
            5. Write risk_score and risk_level back to the record.

        Args:
            federation: res.partner record with is_federation = True.

        Returns:
            dict: {'risk_score': float, 'risk_level': str}
        """
        weights = self._get_weights()
        scores = {
            'budget_depletion': self._score_budget_depletion(federation),
            'yoy_variance':     self._score_yoy_variance(federation),
            'fed_history':      self._score_federation_history(federation),
            'missing_reports':  self._score_missing_reports(federation),
            'performance':      self._score_performance(federation),
        }

        composite = (
            scores['budget_depletion'] * weights['budget_depletion'] +
            scores['yoy_variance']     * weights['yoy_variance'] +
            scores['fed_history']      * weights['fed_history'] +
            scores['missing_reports']  * weights['missing_reports'] +
            scores['performance']      * weights['performance']
        )
        composite = min(max(composite, 0.0), 100.0)
        level = self._level_from_score(composite)

        _logger.info(
            'RiskScorer: federation=%s score=%.2f level=%s dimensions=%s',
            federation.name, composite, level, scores,
        )

        federation.sudo().write({'risk_score': composite, 'risk_level': level})
        return {'risk_score': composite, 'risk_level': level}

    def score_request(self, request):
        """Compute risk indicators for a single support request.

        Uses the federation's current risk score plus request-specific factors
        (variance and requested vs eligible delta).

        Args:
            request: ministry.support.request record.

        Returns:
            dict: {'risk_score': float, 'risk_level': str}
        """
        fed_score = request.federation_id.risk_score or 0.0

        # Variance penalty: every 10% variance adds 5 risk points
        variance_penalty = min(abs(request.variance_pct or 0.0) / 10.0 * 5.0, 30.0)

        composite = min(fed_score + variance_penalty, 100.0)
        level = self._level_from_score(composite)
        return {'risk_score': composite, 'risk_level': level}

    # ── Dimension Scorers ────────────────────────────────────────────────────

    def _score_budget_depletion(self, federation):
        """Score 0–100 based on how much of the annual budget has been consumed.

        Returns:
            float: 0 = no depletion, 100 = fully depleted.
        """
        fiscal_year = self.env['ir.config_parameter'].sudo().get_param(
            'ministry.fiscal_year', str(date.today().year)
        )
        annual_budget = float(
            self.env['ir.config_parameter'].sudo().get_param('ministry.annual_budget', '50000000')
        )
        if annual_budget <= 0:
            return 0.0

        approved = sum(
            self.env['ministry.support.request'].search([
                ('fiscal_year', '=', fiscal_year),
                ('state', 'in', ['approved', 'to_pay', 'paid', 'awaiting_report', 'closed']),
            ]).mapped('approved_amount')
        )
        depletion_ratio = (approved / annual_budget) * 100.0
        return min(depletion_ratio, 100.0)

    def _score_yoy_variance(self, federation):
        """Score based on average YoY variance across all requests in current fiscal year.

        Returns:
            float: 0 = no change, 100 = >100% average variance.
        """
        fiscal_year = self.env['ir.config_parameter'].sudo().get_param(
            'ministry.fiscal_year', str(date.today().year)
        )
        requests = self.env['ministry.support.request'].search([
            ('federation_id', '=', federation.id),
            ('fiscal_year', '=', fiscal_year),
            ('variance_pct', '!=', 0.0),
        ])
        if not requests:
            return 0.0
        avg_variance = sum(abs(r.variance_pct) for r in requests) / len(requests)
        return min(avg_variance, 100.0)

    def _score_federation_history(self, federation):
        """Score based on violations and rejections in the last 12 months.

        Returns:
            float: 0 = clean history, 100 = many violations/rejections.
        """
        cutoff = date.today() - timedelta(days=365)
        violations = self.env['ministry.violation'].search_count([
            ('inspection_id.federation_id', '=', federation.id),
            ('create_date', '>=', cutoff.strftime('%Y-%m-%d')),
        ])
        rejections = self.env['ministry.support.request'].search_count([
            ('federation_id', '=', federation.id),
            ('state', '=', 'rejected'),
            ('create_date', '>=', cutoff.strftime('%Y-%m-%d')),
        ])
        total_events = violations + rejections
        # 5 events = score 100
        return min(total_events / 5.0 * 100.0, 100.0)

    def _score_missing_reports(self, federation):
        """Score based on overdue post-event reports.

        Returns:
            float: 0 = all reports submitted, 100 = 5+ reports missing.
        """
        overdue_requests = self.env['ministry.support.request'].search_count([
            ('federation_id', '=', federation.id),
            ('state', '=', 'awaiting_report'),
        ])
        # 5 missing reports = score 100
        return min(overdue_requests / 5.0 * 100.0, 100.0)

    def _score_performance(self, federation):
        """Score based on average KPI achievement in last 3 post-event reports.

        Lower achievement = higher risk. Score inverted: 0% achievement → 100 risk.

        Returns:
            float: 0 = full achievement (low risk), 100 = zero achievement.
        """
        recent_reports = self.env['ministry.post.event.report'].search([
            ('federation_id', '=', federation.id),
            ('state', '=', 'submitted'),
        ], order='create_date desc', limit=3)

        if not recent_reports:
            return 0.0

        avg_achievement = sum(r.achievement_pct for r in recent_reports) / len(recent_reports)
        # Invert: 100% achievement = 0 risk, 0% achievement = 100 risk
        return max(100.0 - avg_achievement, 0.0)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _get_weights(self):
        """Read scoring weights from system parameters.

        Returns:
            dict: Weight fractions summing to 1.0.
        """
        params = self.env['ir.config_parameter'].sudo()
        w = {
            'budget_depletion': float(params.get_param('ministry.risk_weight_budget_depletion', '30')) / 100.0,
            'yoy_variance':     float(params.get_param('ministry.risk_weight_yoy_variance', '25')) / 100.0,
            'fed_history':      float(params.get_param('ministry.risk_weight_federation_history', '20')) / 100.0,
            'missing_reports':  float(params.get_param('ministry.risk_weight_missing_reports', '15')) / 100.0,
            'performance':      float(params.get_param('ministry.risk_weight_performance', '10')) / 100.0,
        }
        return w

    def _level_from_score(self, score):
        """Determine risk level from composite score.

        Args:
            score: float in range [0, 100].

        Returns:
            str: 'low', 'medium', or 'high'.
        """
        if score < _LEVEL_LOW:
            return 'low'
        if score <= _LEVEL_HIGH:
            return 'medium'
        return 'high'
