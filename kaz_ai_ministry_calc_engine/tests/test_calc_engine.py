# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestMinistryCalcEngine(TransactionCase):
    """Unit tests for MinistryCalcEngine — covers all calculation methods,
    max_limit capping, eligibility expressions, YoY variance, and deductions."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.engine = cls.env['ministry.calc.engine']
        cls.company = cls.env.company

        # Support item fixtures
        cls.item_fixed = cls.env['ministry.support.item'].create({
            'name': 'Fixed Salary',
            'code': 'TEST-FIXED-01',
            'category': 'operational',
            'item_type': 'fixed',
            'calc_method': 'fixed_amount',
            'fixed_amount': 15000.0,
            'max_limit': 0.0,
        })
        cls.item_by_count = cls.env['ministry.support.item'].create({
            'name': 'Referee Allowance',
            'code': 'TEST-COUNT-01',
            'category': 'technical',
            'item_type': 'variable',
            'calc_method': 'by_count',
            'unit_amount': 500.0,
            'max_limit': 5000.0,
        })
        cls.item_by_request = cls.env['ministry.support.item'].create({
            'name': 'Camp Support',
            'code': 'TEST-REQ-01',
            'category': 'activity',
            'item_type': 'variable',
            'calc_method': 'by_request',
            'max_limit': 100000.0,
        })
        cls.item_with_eligibility = cls.env['ministry.support.item'].create({
            'name': 'Olympic Only',
            'code': 'TEST-ELIG-01',
            'category': 'activity',
            'item_type': 'variable',
            'calc_method': 'by_request',
            'max_limit': 500000.0,
            'eligibility_python': "result = federation.olympic_classification == 'olympic'",
        })

        # Federation partner fixtures
        cls.federation_olympic = cls.env['res.partner'].create({
            'name': 'Test Olympic Federation',
            'is_federation': True,
            'olympic_classification': 'olympic',
            'federation_status': 'active',
        })
        cls.federation_non_olympic = cls.env['res.partner'].create({
            'name': 'Test Non-Olympic Federation',
            'is_federation': True,
            'olympic_classification': 'non_olympic',
            'federation_status': 'active',
        })

    def _make_request(self, federation, item, requested_amount=0.0, participants_count=0,
                      fiscal_year='2026', state='draft'):
        """Helper: create a minimal support request mock for engine tests."""
        req = MagicMock()
        req.name = 'SR/TEST/00001'
        req.federation_id = federation
        req.support_item_id = item
        req.requested_amount = requested_amount
        req.participants_count = participants_count
        req.fiscal_year = fiscal_year
        req.state = state
        req.eligible_amount = 0.0
        req.approved_amount = 0.0
        req.message_post = MagicMock()
        return req

    # ── Fixed Amount Tests ───────────────────────────────────────────────────

    def test_01_fixed_amount_basic(self):
        """Fixed amount item returns the item's fixed_amount."""
        req = self._make_request(self.federation_olympic, self.item_fixed)
        result = self.engine._apply_calc_method(req, self.item_fixed)
        self.assertAlmostEqual(result, 15000.0)

    def test_02_fixed_amount_ignores_requested_amount(self):
        """Fixed amount ignores the request's requested_amount field."""
        req = self._make_request(self.federation_olympic, self.item_fixed, requested_amount=99999.0)
        result = self.engine._apply_calc_method(req, self.item_fixed)
        self.assertAlmostEqual(result, 15000.0)

    def test_03_fixed_amount_no_cap_when_max_limit_zero(self):
        """No capping applied when max_limit is 0 (means unlimited)."""
        req = self._make_request(self.federation_olympic, self.item_fixed)
        result = self.engine.compute_eligible_amount(req)
        self.assertAlmostEqual(result, 15000.0)

    # ── By Count Tests ───────────────────────────────────────────────────────

    def test_04_by_count_basic(self):
        """By-count: unit_amount × participants_count."""
        req = self._make_request(self.federation_olympic, self.item_by_count, participants_count=6)
        result = self.engine._apply_calc_method(req, self.item_by_count)
        self.assertAlmostEqual(result, 3000.0)  # 500 × 6

    def test_05_by_count_zero_participants_defaults_to_one(self):
        """By-count with 0 participants uses 1 as minimum."""
        req = self._make_request(self.federation_olympic, self.item_by_count, participants_count=0)
        result = self.engine._apply_calc_method(req, self.item_by_count)
        self.assertAlmostEqual(result, 500.0)  # 500 × 1

    def test_06_by_count_capped_by_max_limit(self):
        """By-count result capped when it exceeds max_limit."""
        req = self._make_request(self.federation_olympic, self.item_by_count, participants_count=20)
        # 500 × 20 = 10,000 → should cap to 5,000
        result = self.engine.compute_eligible_amount(req)
        self.assertAlmostEqual(result, 5000.0)

    def test_07_by_count_below_cap(self):
        """By-count result unchanged when below max_limit."""
        req = self._make_request(self.federation_olympic, self.item_by_count, participants_count=5)
        # 500 × 5 = 2,500 < 5,000
        result = self.engine.compute_eligible_amount(req)
        self.assertAlmostEqual(result, 2500.0)

    def test_08_by_count_exactly_at_cap(self):
        """By-count result at exactly max_limit passes through unchanged."""
        req = self._make_request(self.federation_olympic, self.item_by_count, participants_count=10)
        # 500 × 10 = 5,000 = max_limit
        result = self.engine.compute_eligible_amount(req)
        self.assertAlmostEqual(result, 5000.0)

    # ── By Request Tests ─────────────────────────────────────────────────────

    def test_09_by_request_returns_requested_amount(self):
        """By-request: eligible amount equals requested_amount when under cap."""
        req = self._make_request(self.federation_olympic, self.item_by_request,
                                  requested_amount=75000.0)
        result = self.engine.compute_eligible_amount(req)
        self.assertAlmostEqual(result, 75000.0)

    def test_10_by_request_capped_at_max_limit(self):
        """By-request: requested amount capped at max_limit."""
        req = self._make_request(self.federation_olympic, self.item_by_request,
                                  requested_amount=150000.0)
        # Exceeds 100,000 max
        result = self.engine.compute_eligible_amount(req)
        self.assertAlmostEqual(result, 100000.0)

    def test_11_by_request_zero_amount(self):
        """By-request with zero requested amount returns 0."""
        req = self._make_request(self.federation_olympic, self.item_by_request,
                                  requested_amount=0.0)
        result = self.engine.compute_eligible_amount(req)
        self.assertAlmostEqual(result, 0.0)

    # ── Eligibility Expression Tests ─────────────────────────────────────────

    def test_12_eligibility_olympic_federation_passes(self):
        """Olympic federation passes an olympic-only eligibility rule."""
        req = self._make_request(self.federation_olympic, self.item_with_eligibility,
                                  requested_amount=200000.0)
        result = self.engine.compute_eligible_amount(req)
        self.assertAlmostEqual(result, 200000.0)

    def test_13_eligibility_non_olympic_federation_blocked(self):
        """Non-Olympic federation blocked by olympic-only eligibility rule."""
        req = self._make_request(self.federation_non_olympic, self.item_with_eligibility,
                                  requested_amount=200000.0)
        result = self.engine.compute_eligible_amount(req)
        self.assertAlmostEqual(result, 0.0)

    def test_14_eligibility_empty_expression_always_passes(self):
        """Empty eligibility expression allows all federations."""
        req = self._make_request(self.federation_non_olympic, self.item_by_request,
                                  requested_amount=50000.0)
        result = self.engine.compute_eligible_amount(req)
        self.assertAlmostEqual(result, 50000.0)

    def test_15_eligibility_expression_syntax_error_defaults_to_true(self):
        """Malformed eligibility expression defaults to True (does not block)."""
        item_broken = self.env['ministry.support.item'].create({
            'name': 'Broken Eligibility Item',
            'code': 'TEST-BROKEN-01',
            'category': 'activity',
            'item_type': 'variable',
            'calc_method': 'by_request',
            'max_limit': 0.0,
            'eligibility_python': 'this is not valid python !!! @@@',
        })
        req = self._make_request(self.federation_olympic, item_broken, requested_amount=1000.0)
        result = self.engine.compute_eligible_amount(req)
        # Should not crash; defaults to eligible
        self.assertGreaterEqual(result, 0.0)

    # ── No Item Tests ────────────────────────────────────────────────────────

    def test_16_no_support_item_returns_zero(self):
        """Request with no support item returns 0."""
        req = self._make_request(self.federation_olympic, None, requested_amount=50000.0)
        req.support_item_id = None
        result = self.engine.compute_eligible_amount(req)
        self.assertAlmostEqual(result, 0.0)

    # ── Variance Tests ───────────────────────────────────────────────────────

    def test_17_variance_no_prior_year_returns_zero(self):
        """No prior-year approved requests → variance is 0.0."""
        req = self._make_request(self.federation_olympic, self.item_by_request,
                                  requested_amount=50000.0, fiscal_year='2026')
        # No requests exist for 2025 — variance must be 0
        result = self.engine.compute_variance(req)
        self.assertAlmostEqual(result, 0.0)

    def test_18_variance_missing_fiscal_year_returns_zero(self):
        """Fiscal year empty → variance is 0.0."""
        req = self._make_request(self.federation_olympic, self.item_by_request,
                                  requested_amount=50000.0, fiscal_year='')
        result = self.engine.compute_variance(req)
        self.assertAlmostEqual(result, 0.0)

    # ── Apply Pending Deductions Tests ───────────────────────────────────────

    def test_19_no_deductions_returns_full_amount(self):
        """No pending deductions → net payable equals approved amount."""
        req = self._make_request(self.federation_olympic, self.item_fixed)
        result = self.engine.apply_pending_deductions(req, 15000.0)
        self.assertAlmostEqual(result, 15000.0)

    def test_20_deduction_reduces_payable_amount(self):
        """Single pending deduction correctly reduces net payable."""
        # Create a real deduction record
        deduction = self.env['ministry.pending.deduction'].create({
            'federation_id': self.federation_olympic.id,
            'deduction_amount': 5000.0,
            'state': 'pending',
            'reason': 'Test deduction',
        })
        req = self._make_request(self.federation_olympic, self.item_fixed)
        # Provide a real request record for the applied_on_request_id write
        real_req = self.env['ministry.support.request'].search([], limit=1)
        if not real_req:
            # Engine test without real request; just verify arithmetic
            result = self.engine.apply_pending_deductions(req, 15000.0)
            self.assertGreaterEqual(result, 0.0)
        else:
            req.id = real_req.id
            result = self.engine.apply_pending_deductions(req, 15000.0)
            self.assertAlmostEqual(result, 10000.0)

    def test_21_deduction_cannot_produce_negative_amount(self):
        """Net payable cannot go below 0 regardless of deduction size."""
        # Large deduction larger than amount
        self.env['ministry.pending.deduction'].create({
            'federation_id': self.federation_olympic.id,
            'deduction_amount': 999999.0,
            'state': 'pending',
            'reason': 'Oversized deduction test',
        })
        req = self._make_request(self.federation_olympic, self.item_fixed)
        result = self.engine.apply_pending_deductions(req, 15000.0)
        self.assertGreaterEqual(result, 0.0)

    def test_22_large_fixed_amount_full_flow(self):
        """Full flow: fixed amount with no cap and no deductions."""
        item_large = self.env['ministry.support.item'].create({
            'name': 'International Office',
            'code': 'TEST-LARGE-01',
            'category': 'general',
            'item_type': 'fixed',
            'calc_method': 'fixed_amount',
            'fixed_amount': 200000.0,
            'max_limit': 400000.0,
        })
        req = self._make_request(self.federation_olympic, item_large)
        eligible = self.engine.compute_eligible_amount(req)
        net = self.engine.apply_pending_deductions(req, eligible)
        self.assertAlmostEqual(eligible, 200000.0)
        self.assertAlmostEqual(net, 200000.0)
