/** @odoo-module **/

import { Component, onMounted, onWillStart, onWillUnmount, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class MinistryDashboard extends Component {
    static template = "kaz_ai_ministry_dashboard.MinistryDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.dashboardRef = useRef("dashboard");
        this.state = useState({
            loading: true,
            refreshing: false,
            data: null,
        });

        onWillStart(async () => {
            await this.loadData();
        });

        onMounted(() => {
            this.interval = setInterval(() => this.loadData({ silent: true }), 60000);
        });

        onWillUnmount(() => {
            if (this.interval) {
                clearInterval(this.interval);
            }
        });
    }

    async loadData(options = {}) {
        if (!options.silent) {
            this.state.refreshing = true;
        }
        try {
            const data = await this.orm.call("ministry.dashboard.service", "get_dashboard_data", []);
            this.state.data = this.normalizeData(data);
        } catch (error) {
            if (!this.state.data) {
                this.state.data = this.normalizeData();
            }
            console.error("Ministry dashboard data load failed", error);
            if (!options.silent) {
                this.notification.add("Dashboard data could not be loaded.", { type: "danger" });
            }
        } finally {
            this.state.loading = false;
            this.state.refreshing = false;
        }
    }

    normalizeData(data = {}) {
        return {
            currency: data.currency || "AED",
            fiscal_year: data.fiscal_year || new Date().getFullYear(),
            last_updated: data.last_updated || new Date().toISOString(),
            kpis: {
                annual_budget: 0,
                total_spent: 0,
                remaining: 0,
                burn_pct: 0,
                request_count: 0,
                open_request_count: 0,
                pending_review: 0,
                pending_payments: 0,
                awaiting_reports: 0,
                risk_indicator: 0,
                approval_rate: 0,
                ...(data.kpis || {}),
            },
            risk_counts: { low: 0, medium: 0, high: 0, ...(data.risk_counts || {}) },
            pipeline: data.pipeline || [],
            support_by_federation: data.support_by_federation || [],
            support_by_category: data.support_by_category || [],
            monthly_spending: data.monthly_spending || [],
            recent_requests: data.recent_requests || [],
            alerts: data.alerts || [],
            actions: data.actions || {},
        };
    }

    async openAction(key) {
        const action = this.state.data?.actions?.[key];
        if (action) {
            await this.action.doAction({
                ...action,
                view_mode: action.view_mode || "list,form",
                views: action.views || [[false, "list"], [false, "form"]],
                domain: action.domain || [],
            });
        }
    }

    scrollDashboard(position) {
        const dashboard = this.dashboardRef.el;
        const top = position === "top" ? 0 : dashboard?.scrollHeight || 0;
        if (dashboard && dashboard.scrollHeight > dashboard.clientHeight) {
            dashboard.scrollTo({ top, behavior: "smooth" });
        } else {
            window.scrollTo({ top, behavior: "smooth" });
        }
    }

    formatMoney(value) {
        return new Intl.NumberFormat("en-AE", {
            style: "currency",
            currency: this.state.data?.currency || "AED",
            maximumFractionDigits: 0,
        }).format(value || 0);
    }

    formatNumber(value) {
        return new Intl.NumberFormat("en-AE", { maximumFractionDigits: 0 }).format(value || 0);
    }

    formatPercent(value) {
        return `${new Intl.NumberFormat("en-AE", { maximumFractionDigits: 1 }).format(value || 0)}%`;
    }

    formatDateTime(value) {
        if (!value) {
            return "";
        }
        return new Intl.DateTimeFormat("en-AE", {
            day: "2-digit",
            month: "short",
            hour: "2-digit",
            minute: "2-digit",
        }).format(new Date(value));
    }

    widthStyle(value) {
        const pct = Math.min(100, Math.max(2, Number(value) || 0));
        return `inline-size: ${pct}%`;
    }

    heightStyle(value) {
        const pct = Number(value) || 0;
        const height = pct ? Math.min(176, Math.max(8, Math.round(pct * 1.76))) : 2;
        return `block-size: ${height}px`;
    }

    riskClass(level) {
        return `o_ministry_chip o_ministry_chip--${level || "low"}`;
    }

    severityClass(level) {
        return `o_ministry_alert o_ministry_alert--${level || "info"}`;
    }

    stateClass(state) {
        const map = {
            draft: "muted",
            submitted: "warning",
            under_review: "warning",
            returned: "blocked",
            rejected: "blocked",
            approved: "success",
            to_pay: "warning",
            paid: "success",
            awaiting_report: "warning",
            closed: "success",
        };
        return `o_ministry_state o_ministry_state--${map[state] || "muted"}`;
    }
}

registry.category("actions").add("kaz_ai_ministry_dashboard.dashboard", MinistryDashboard);
