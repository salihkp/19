# -*- coding: utf-8 -*-

from collections import defaultdict
from datetime import date

from odoo import api, fields, models


class MinistryDashboardService(models.AbstractModel):
    _name = "ministry.dashboard.service"
    _description = "Ministry Dashboard Service"

    @api.model
    def get_dashboard_data(self):
        Request = self.env["ministry.support.request"].sudo()
        Param = self.env["ir.config_parameter"].sudo()
        annual_budget = float(
            Param.get_param("ministry.annual_master_budget")
            or Param.get_param("ministry.annual_budget")
            or "50000000"
        )
        fiscal_year = str(Param.get_param("ministry.fiscal_year") or fields.Date.context_today(self).year)

        requests = Request.search([("fiscal_year", "=", fiscal_year)])
        if not requests:
            requests = Request.search([])

        spent_states = ["approved", "to_pay", "paid", "awaiting_report", "closed"]
        open_states = ["submitted", "under_review", "returned", "approved", "to_pay", "awaiting_report"]
        spent_requests = requests.filtered(lambda req: req.state in spent_states)
        open_requests = requests.filtered(lambda req: req.state in open_states)

        total_spent = sum(req.approved_amount or req.eligible_amount or 0.0 for req in spent_requests)
        pending_payments = sum(
            req.approved_amount or req.eligible_amount or 0.0
            for req in requests.filtered(lambda req: req.state in ["approved", "to_pay"])
        )
        remaining = max(annual_budget - total_spent, 0.0)
        burn_pct = min((total_spent / annual_budget * 100.0) if annual_budget else 0.0, 100.0)

        approved_like = requests.filtered(lambda req: req.state in ["approved", "to_pay", "paid", "awaiting_report", "closed"])
        decided = requests.filtered(lambda req: req.state not in ["draft", "submitted", "under_review", "returned"])
        approval_rate = (len(approved_like) / len(decided) * 100.0) if decided else 0.0

        risk_counts = self._risk_counts(requests)
        state_counts = self._state_counts(requests)

        return {
            "currency": "AED",
            "fiscal_year": fiscal_year,
            "last_updated": fields.Datetime.now(),
            "kpis": {
                "annual_budget": annual_budget,
                "total_spent": total_spent,
                "remaining": remaining,
                "burn_pct": round(burn_pct, 1),
                "request_count": len(requests),
                "open_request_count": len(open_requests),
                "pending_review": state_counts["submitted"] + state_counts["under_review"],
                "pending_payments": pending_payments,
                "awaiting_reports": state_counts["awaiting_report"],
                "risk_indicator": risk_counts["high"],
                "approval_rate": round(approval_rate, 1),
            },
            "risk_counts": risk_counts,
            "pipeline": self._pipeline(state_counts, len(requests)),
            "support_by_federation": self._support_by_federation(requests, spent_states),
            "support_by_category": self._support_by_category(requests, spent_states),
            "monthly_spending": self._monthly_spending(spent_requests),
            "recent_requests": self._recent_requests(requests),
            "alerts": self._alerts(),
            "actions": {
                "requests": self._action_for_model("ministry.support.request", name="All Support Requests"),
                "review": self._action_for_model(
                    "ministry.support.request",
                    [("state", "in", ["submitted", "under_review"])],
                    name="Requests Under Review",
                ),
                "payments": self._action_for_model(
                    "ministry.support.request",
                    [("state", "in", ["approved", "to_pay"])],
                    name="Pending Payments",
                ),
                "risk": self._action_for_model(
                    "ministry.support.request",
                    [("risk_level", "=", "high")],
                    name="High Risk Requests",
                ),
                "approved": self._action_for_model(
                    "ministry.support.request",
                    [("state", "in", ["approved", "to_pay", "paid", "awaiting_report", "closed"])],
                    name="Approved Requests",
                ),
                "federations": self._action_for_model(
                    "res.partner",
                    [("is_federation", "=", True)],
                    name="Federations",
                ),
                "alerts": self._action_for_model("ministry.analytics.alert", name="Analytics Alerts"),
                "reports": self._action_for_model(
                    "ministry.support.request",
                    [("state", "=", "awaiting_report")],
                    name="Requests Awaiting Reports",
                ),
            },
        }

    @api.model
    def _state_counts(self, requests):
        counts = defaultdict(int)
        for req in requests:
            counts[req.state] += 1
        return counts

    @api.model
    def _risk_counts(self, requests):
        return {
            "low": len(requests.filtered(lambda req: req.risk_level == "low")),
            "medium": len(requests.filtered(lambda req: req.risk_level == "medium")),
            "high": len(requests.filtered(lambda req: req.risk_level == "high")),
        }

    @api.model
    def _pipeline(self, state_counts, total):
        stages = [
            ("Draft", state_counts["draft"], "draft"),
            ("Submitted", state_counts["submitted"] + state_counts["under_review"], "review"),
            ("Approved", state_counts["approved"] + state_counts["to_pay"], "approved"),
            ("Paid", state_counts["paid"] + state_counts["awaiting_report"], "paid"),
            ("Closed", state_counts["closed"], "closed"),
            ("Returned/Rejected", state_counts["returned"] + state_counts["rejected"], "blocked"),
        ]
        baseline = max(total, 1)
        return [
            {
                "label": label,
                "value": value,
                "key": key,
                "pct": round((value / baseline) * 100.0, 1),
            }
            for label, value, key in stages
        ]

    @api.model
    def _support_by_federation(self, requests, spent_states):
        federations = self.env["res.partner"].sudo().search([("is_federation", "=", True)])
        rows = []
        for fed in federations:
            fed_requests = requests.filtered(lambda req, fed=fed: req.federation_id.id == fed.id)
            spent = fed_requests.filtered(lambda req: req.state in spent_states)
            rows.append({
                "label": self._clean_federation_name(fed.display_name),
                "value": round(sum(req.approved_amount or req.eligible_amount or 0.0 for req in spent), 2),
                "request_count": len(fed_requests),
                "risk_level": fed.risk_level or "low",
                "risk_score": round(fed.risk_score or 0.0, 1),
            })
        return self._with_percentages(rows, limit=8)

    @api.model
    def _support_by_category(self, requests, spent_states):
        labels = {
            "operational": "Operational",
            "technical": "Technical",
            "general": "General Financial",
            "activity": "Activity",
        }
        colors = {
            "operational": "#8B6F2A",
            "technical": "#00732F",
            "general": "#42526A",
            "activity": "#C8102E",
        }
        rows = []
        for key, label in labels.items():
            cat_requests = requests.filtered(lambda req, key=key: req.category == key and req.state in spent_states)
            rows.append({
                "key": key,
                "label": label,
                "value": round(sum(req.approved_amount or req.eligible_amount or 0.0 for req in cat_requests), 2),
                "request_count": len(cat_requests),
                "color": colors[key],
            })
        return self._with_percentages(rows, limit=8)

    @api.model
    def _monthly_spending(self, spent_requests):
        monthly = defaultdict(float)
        for req in spent_requests:
            month = req.approval_date or req.write_date or req.create_date
            if month:
                monthly[fields.Datetime.to_datetime(month).strftime("%b")] += req.approved_amount or req.eligible_amount or 0.0

        rows = [{"label": label, "value": round(monthly.get(label, 0.0), 2)} for label in self._last_12_month_labels()]
        max_value = max([row["value"] for row in rows] or [1.0])
        for row in rows:
            row["pct"] = round((row["value"] / max_value) * 100.0, 1) if max_value else 0.0
        return rows

    @api.model
    def _recent_requests(self, requests):
        state_labels = dict(self.env["ministry.support.request"]._fields["state"].selection)
        category_labels = {
            "operational": "Operational",
            "technical": "Technical",
            "general": "General",
            "activity": "Activity",
        }
        rows = []
        for req in requests.sorted(lambda rec: rec.write_date or rec.create_date, reverse=True)[:8]:
            rows.append({
                "id": req.id,
                "name": req.name,
                "federation": self._clean_federation_name(req.federation_id.display_name),
                "category": category_labels.get(req.category, req.category or "Other"),
                "amount": req.approved_amount or req.eligible_amount or req.requested_amount or 0.0,
                "state": req.state,
                "state_label": state_labels.get(req.state, req.state),
                "risk_level": req.risk_level or "low",
            })
        return rows

    @api.model
    def _alerts(self):
        if "ministry.analytics.alert" not in self.env:
            return []
        Alert = self.env["ministry.analytics.alert"].sudo()
        alerts = Alert.search([("is_acknowledged", "=", False)], order="create_date desc", limit=5)
        return [
            {
                "name": alert.name,
                "severity": alert.severity,
                "federation": self._clean_federation_name(alert.federation_id.display_name) if alert.federation_id else "",
                "detail": alert.detail or "",
            }
            for alert in alerts
        ]

    @api.model
    def _with_percentages(self, rows, limit=8):
        rows = sorted(rows, key=lambda row: row["value"], reverse=True)[:limit]
        max_value = max([row["value"] for row in rows] or [1.0])
        for row in rows:
            row["pct"] = round((row["value"] / max_value) * 100.0, 1) if max_value else 0.0
        return rows

    @api.model
    def _last_12_month_labels(self):
        today = date.today()
        labels = []
        for offset in range(11, -1, -1):
            month = today.month - offset
            year = today.year
            while month <= 0:
                month += 12
                year -= 1
            labels.append(date(year, month, 1).strftime("%b"))
        return labels

    @api.model
    def _clean_federation_name(self, name):
        return (name or "Unassigned").replace(" Federation Admin", " Federation").replace(" Admin", "")

    @api.model
    def _action_for_model(self, model, domain=None, name=None):
        return {
            "type": "ir.actions.act_window",
            "name": name or self.env[model]._description,
            "res_model": model,
            "view_mode": "list,form",
            "views": [(False, "list"), (False, "form")],
            "domain": domain or [],
            "target": "current",
        }
