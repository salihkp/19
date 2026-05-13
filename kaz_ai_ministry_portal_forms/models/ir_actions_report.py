# -*- coding: utf-8 -*-
from odoo import api, models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    _MINISTRY_PORTAL_REPORT_NAMES = {
        'kaz_ai_ministry_portal_forms.report_participation',
        'kaz_ai_ministry_portal_forms.report_per',
        'kaz_ai_ministry_portal_forms.report_hosting',
    }

    def _is_ministry_portal_report(self, report_ref=False):
        if self.env.context.get('ministry_portal_force_pdf_utf8'):
            return True

        if report_ref:
            try:
                report = self._get_report(report_ref)
            except (ValueError, TypeError):
                report = self.env['ir.actions.report']
            if report and report.report_name in self._MINISTRY_PORTAL_REPORT_NAMES:
                return True

        return len(self) == 1 and self.report_name in self._MINISTRY_PORTAL_REPORT_NAMES

    @api.model
    def _run_wkhtmltopdf(
            self,
            bodies,
            report_ref=False,
            header=None,
            footer=None,
            landscape=False,
            specific_paperformat_args=None,
            set_viewport_size=False):
        if (
            self._is_ministry_portal_report(report_ref)
            and not self.env.context.get('ministry_portal_force_pdf_utf8')
        ):
            return self.with_context(ministry_portal_force_pdf_utf8=True)._run_wkhtmltopdf(
                bodies,
                report_ref=report_ref,
                header=header,
                footer=footer,
                landscape=landscape,
                specific_paperformat_args=specific_paperformat_args,
                set_viewport_size=set_viewport_size,
            )
        return super()._run_wkhtmltopdf(
            bodies,
            report_ref=report_ref,
            header=header,
            footer=footer,
            landscape=landscape,
            specific_paperformat_args=specific_paperformat_args,
            set_viewport_size=set_viewport_size,
        )

    @api.model
    def _build_wkhtmltopdf_args(
            self,
            paperformat_id,
            landscape,
            specific_paperformat_args=None,
            set_viewport_size=False):
        command_args = super()._build_wkhtmltopdf_args(
            paperformat_id,
            landscape,
            specific_paperformat_args=specific_paperformat_args,
            set_viewport_size=set_viewport_size,
        )
        # Odoo writes split report bodies to temp HTML files; wkhtmltopdf may
        # otherwise guess a legacy encoding and render Arabic as mojibake.
        if self.env.context.get('ministry_portal_force_pdf_utf8') and '--encoding' not in command_args:
            command_args[0:0] = ['--encoding', 'utf-8']
        return command_args
