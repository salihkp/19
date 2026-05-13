# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestMinistryRiskScorer(TransactionCase):
    """Unit tests for MinistryRiskScorer covering all five dimensions,
    composite score calculation, threshold classification, and edge cases."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.scorer = cls.env['ministry.risk.scorer']

        cls.fed_clean = cls.env['res.partner'].create({
            'name': 'Risk Test — Clean Federation',
            'is_federation': True,
            'olympic_classification': 'olympic',
            'federation_status': 'active',
            'risk_score': 0.0,
            'risk_level': 'low',
        })
        cls.fed_risky = cls.env['res.partner'].create({
            'name': 'Risk Test — Risky Federation',
            'is_federation': True,
            'olympic_classification': 'non_olympic',
            'federation_status': 'active',
            'risk_score': 75.0,
            'risk_level': 'high',
        })

    # ── Level Threshold Tests ────────────────────────────────────────────────

    def test_01_low_risk_threshold(self):
        """Score below 35 classifies as low risk."""
        level = self.scorer._level_from_score(20.0)
        self.assertEqual(level, 'low')

    def test_02_medium_risk_lower_boundary(self):
        """Score at exactly 35 classifies as medium risk."""
        level = self.scorer._level_from_score(35.0)
        self.assertEqual(level, 'medium')

    def test_03_medium_risk_upper_boundary(self):
        """Score at exactly 65 classifies as medium risk."""
        level = self.scorer._level_from_score(65.0)
        self.assertEqual(level, 'medium')

    def test_04_high_risk_threshold(self):
        """Score above 65 classifies as high risk."""
        level = self.scorer._level_from_score(66.0)
        self.assertEqual(level, 'high')

    def test_05_zero_score_is_low(self):
        """Score of 0 is classified as low risk."""
        self.assertEqual(self.scorer._level_from_score(0.0), 'low')

    def test_06_hundred_score_is_high(self):
        """Score of 100 is classified as high risk."""
        self.assertEqual(self.scorer._level_from_score(100.0), 'high')

    # ── Weight Configuration Tests ────────────────────────────────────────────

    def test_07_weights_sum_to_one(self):
        """Configured weights should sum to approximately 1.0."""
        weights = self.scorer._get_weights()
        total = sum(weights.values())
        self.assertAlmostEqual(total, 1.0, places=2)

    def test_08_default_weights_match_spec(self):
        """Default weights match the design spec (30/25/20/15/10)."""
        weights = self.scorer._get_weights()
        self.assertAlmostEqual(weights['budget_depletion'], 0.30, places=2)
        self.assertAlmostEqual(weights['yoy_variance'],     0.25, places=2)
        self.assertAlmostEqual(weights['fed_history'],      0.20, places=2)
        self.assertAlmostEqual(weights['missing_reports'],  0.15, places=2)
        self.assertAlmostEqual(weights['performance'],      0.10, places=2)

    # ── Dimension Score Tests ─────────────────────────────────────────────────

    def test_09_missing_reports_score_zero_when_none_overdue(self):
        """Missing reports dimension is 0 when no requests await reports."""
        score = self.scorer._score_missing_reports(self.fed_clean)
        self.assertAlmostEqual(score, 0.0)

    def test_10_performance_score_zero_when_no_reports(self):
        """Performance dimension is 0 when no post-event reports exist."""
        score = self.scorer._score_performance(self.fed_clean)
        self.assertAlmostEqual(score, 0.0)

    def test_11_history_score_zero_clean_federation(self):
        """History dimension is 0 for federation with no violations or rejections."""
        score = self.scorer._score_federation_history(self.fed_clean)
        self.assertAlmostEqual(score, 0.0)

    def test_12_composite_score_persisted_to_partner(self):
        """score_federation writes risk_score and risk_level back to the partner."""
        result = self.scorer.score_federation(self.fed_clean)
        self.fed_clean.invalidate_recordset()
        self.assertAlmostEqual(self.fed_clean.risk_score, result['risk_score'])
        self.assertEqual(self.fed_clean.risk_level, result['risk_level'])

    def test_13_composite_score_bounded_0_to_100(self):
        """Composite score is always within [0, 100] range."""
        result = self.scorer.score_federation(self.fed_risky)
        self.assertGreaterEqual(result['risk_score'], 0.0)
        self.assertLessEqual(result['risk_score'], 100.0)
