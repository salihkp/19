# -*- coding: utf-8 -*-
import io

import xlsxwriter
from werkzeug.exceptions import Forbidden

from odoo import fields, http
from odoo.http import content_disposition, request


class MinistryFinancialReports(http.Controller):
    """Generated Ministry financial support reports."""

    _allowed_report_groups = (
        'kaz_ai_ministry_branding.group_ministry_manager',
        'kaz_ai_ministry_branding.group_ministry_officer_financial',
        'kaz_ai_ministry_branding.group_ministry_officer_technical',
        'kaz_ai_ministry_branding.group_ministry_dept_head',
        'kaz_ai_ministry_branding.group_ministry_analyst',
    )

    _financial_line_keys = (
        'lump_sum',
        'salaries',
        'general_expenses',
        'end_of_service',
        'housing_allowance',
        'rent',
        'rewards',
        'subscriptions',
        'arab_hq',
        'asian_hq',
        'meetings',
        'training_centers',
        'referees',
        'participations',
    )

    _support_item_line_map = {
        'OP-SAL-01': 'salaries',
        'OP-EOS-01': 'end_of_service',
        'OP-RENT-01': 'rent',
        'OP-ELEC-01': 'general_expenses',
        'OP-SEC-01': 'general_expenses',
        'OP-COM-01': 'general_expenses',
        'GEN-PUR-01': 'general_expenses',
        'GEN-HOS-01': 'general_expenses',
        'GEN-STA-01': 'general_expenses',
        'GEN-SYS-01': 'general_expenses',
        'TEC-REW-01': 'rewards',
        'GEN-SUB-01': 'subscriptions',
        'GEN-FEE-01': 'subscriptions',
        'ACT-MEET-01': 'meetings',
        'ACT-CAMP-LOCAL': 'training_centers',
        'ACT-CAMP-ARAB': 'training_centers',
        'TEC-REF-01': 'referees',
        'ACT-PART-LOCAL': 'participations',
        'ACT-PART-ARAB': 'participations',
        'ACT-PART-REG': 'participations',
        'ACT-PART-ASIAN': 'participations',
        'ACT-PART-INTL': 'participations',
        'ACT-PART-OLY': 'participations',
        'TEC-GAME-01': 'participations',
    }

    _approved_states = ('approved', 'to_pay', 'paid', 'awaiting_report', 'closed')

    def _require_report_access(self):
        if request.env.user.has_group('base.group_system'):
            return
        if not any(request.env.user.has_group(group) for group in self._allowed_report_groups):
            raise Forbidden('Your user is not allowed to generate Ministry financial reports.')

    def _fiscal_year(self, fiscal_year=None):
        return fiscal_year or request.env['ir.config_parameter'].sudo().get_param(
            'ministry.fiscal_year', '2026'
        )

    def _empty_amounts(self):
        return {key: 0.0 for key in self._financial_line_keys}

    def _amount_for_request(self, support_request):
        return (
            support_request.approved_amount
            or support_request.net_payable
            or support_request.eligible_amount
            or 0.0
        )

    def _line_key_for_request(self, support_request):
        code = support_request.support_item_id.code or ''
        return self._support_item_line_map.get(code, 'lump_sum')

    def _is_chess_club(self, club):
        sport_name = (club.federation_id.sport_id.name or '').lower()
        federation_name = (club.federation_id.name or '').lower()
        return 'chess' in sport_name or 'chess' in federation_name or 'شطرنج' in sport_name or 'شطرنج' in federation_name

    def _olympic_label(self, federation):
        return 'اولمبي' if federation.olympic_classification == 'olympic' else 'غير اولمبي'

    def _collect_report_data(self, fiscal_year):
        Federation = request.env['res.partner'].sudo()
        SupportRequest = request.env['ministry.support.request'].sudo()
        Club = request.env['ministry.club'].sudo()

        federations = Federation.search(
            [('is_federation', '=', True), ('active', '=', True)],
            order='olympic_classification, name',
        )
        support_requests = SupportRequest.search([
            ('fiscal_year', '=', fiscal_year),
            ('state', 'in', self._approved_states),
        ], order='federation_id, support_item_id, name')

        federation_amounts = {federation.id: self._empty_amounts() for federation in federations}
        request_details = []
        for support_request in support_requests:
            federation = support_request.federation_id
            if federation.id not in federation_amounts:
                federation_amounts[federation.id] = self._empty_amounts()
            line_key = self._line_key_for_request(support_request)
            amount = self._amount_for_request(support_request)
            federation_amounts[federation.id][line_key] += amount
            request_details.append({
                'reference': support_request.name,
                'federation': federation.name,
                'support_item': support_request.support_item_id.name,
                'support_code': support_request.support_item_id.code,
                'state': dict(support_request._fields['state'].selection).get(support_request.state, support_request.state),
                'category': dict(support_request.support_item_id._fields['category'].selection).get(
                    support_request.category, support_request.category
                ),
                'requested_amount': support_request.requested_amount,
                'eligible_amount': support_request.eligible_amount,
                'approved_amount': support_request.approved_amount,
                'net_payable': support_request.net_payable,
                'report_line': line_key,
            })

        clubs = Club.search([('active', '=', True)], order='federation_id, name')
        chess_clubs = clubs.filtered(self._is_chess_club)
        sports_clubs = clubs - chess_clubs

        return {
            'fiscal_year': fiscal_year,
            'generated_on': fields.Datetime.context_timestamp(request.env.user, fields.Datetime.now()),
            'federations': federations,
            'federation_amounts': federation_amounts,
            'support_requests': support_requests,
            'request_details': request_details,
            'sports_clubs': sports_clubs,
            'specialized_clubs': Club.browse(),
            'chess_clubs': chess_clubs,
        }

    def _formats(self, workbook):
        base = {
            'font_name': 'Arial',
            'font_size': 10,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
            'reading_order': 2,
        }
        return {
            'title': workbook.add_format({
                **base,
                'bold': True,
                'font_size': 14,
                'bg_color': '#D9EAD3',
            }),
            'section': workbook.add_format({
                **base,
                'bold': True,
                'font_size': 12,
                'bg_color': '#D9EAD3',
            }),
            'header': workbook.add_format({
                **base,
                'bold': True,
                'bg_color': '#B6D7A8',
            }),
            'text': workbook.add_format({
                **base,
                'align': 'right',
            }),
            'number': workbook.add_format({
                **base,
                'num_format': '#,##0.00',
            }),
            'integer': workbook.add_format({
                **base,
                'num_format': '0',
            }),
            'total': workbook.add_format({
                **base,
                'bold': True,
                'bg_color': '#FFF2CC',
                'num_format': '#,##0.00',
            }),
            'total_text': workbook.add_format({
                **base,
                'bold': True,
                'bg_color': '#FFF2CC',
                'align': 'right',
            }),
            'detail_header': workbook.add_format({
                'font_name': 'Arial',
                'font_size': 10,
                'bold': True,
                'border': 1,
                'align': 'center',
                'valign': 'vcenter',
                'bg_color': '#D9EAD3',
            }),
            'detail_text': workbook.add_format({
                'font_name': 'Arial',
                'font_size': 10,
                'border': 1,
                'align': 'left',
                'valign': 'vcenter',
            }),
            'detail_number': workbook.add_format({
                'font_name': 'Arial',
                'font_size': 10,
                'border': 1,
                'align': 'right',
                'valign': 'vcenter',
                'num_format': '#,##0.00',
            }),
        }

    def _write_federation_block(self, worksheet, formats, data):
        headers = [
            'م',
            'الجهة الرياضية',
            'نوع الجهة',
            'مبلغ مقطوع',
            'الرواتب',
            'مصروفات عامة',
            'نهاية الخدمة',
            'بدل سكن',
            'إيجارات',
            'جوائز',
            'اشتراكات',
            'استضافة مقر العربي',
            'استضافة مقر الآسيوي',
            'اجتماعات',
            'مراكز تدريب',
            'حكام',
            'مشاركات',
            'الإجمالي',
        ]
        worksheet.merge_range(0, 0, 0, 17, f"الدعم المالي للجهات الرياضية {data['fiscal_year']}", formats['title'])
        for col, header in enumerate(headers):
            worksheet.write(1, col, header, formats['header'])

        row = 2
        for sequence, federation in enumerate(data['federations'], start=1):
            amounts = data['federation_amounts'].get(federation.id, self._empty_amounts())
            worksheet.write(row, 0, sequence, formats['integer'])
            worksheet.write(row, 1, federation.name, formats['text'])
            worksheet.write(row, 2, self._olympic_label(federation), formats['text'])
            total = 0.0
            for offset, key in enumerate(self._financial_line_keys, start=3):
                amount = amounts.get(key, 0.0)
                total += amount
                worksheet.write(row, offset, amount, formats['number'])
            worksheet.write(row, 17, total, formats['number'])
            row += 1

        worksheet.merge_range(row, 0, row, 2, 'الإجمالي', formats['total_text'])
        for col in range(3, 18):
            worksheet.write_formula(row, col, f'=SUM({xlsxwriter.utility.xl_rowcol_to_cell(2, col)}:{xlsxwriter.utility.xl_rowcol_to_cell(row - 1, col)})', formats['total'])
        return row + 2

    def _write_club_block(self, worksheet, formats, start_row, start_col, title, clubs, columns):
        worksheet.merge_range(start_row, start_col, start_row, start_col + len(columns) - 1, title, formats['section'])
        for offset, header in enumerate(columns):
            worksheet.write(start_row + 1, start_col + offset, header, formats['header'])

        row = start_row + 2
        amount_columns = len(columns) - 2
        has_rows = bool(clubs)
        for sequence, club in enumerate(clubs, start=1):
            worksheet.write(row, start_col, sequence, formats['integer'])
            worksheet.write(row, start_col + 1, club.name, formats['text'])
            for offset in range(amount_columns):
                worksheet.write(row, start_col + 2 + offset, 0.0, formats['number'])
            row += 1

        worksheet.merge_range(row, start_col, row, start_col + 1, 'الإجمالي', formats['total_text'])
        for col in range(start_col + 2, start_col + len(columns)):
            if has_rows:
                first = xlsxwriter.utility.xl_rowcol_to_cell(start_row + 2, col)
                last = xlsxwriter.utility.xl_rowcol_to_cell(row - 1, col)
                worksheet.write_formula(row, col, f'=SUM({first}:{last})', formats['total'])
            else:
                worksheet.write(row, col, 0.0, formats['total'])
        return row

    def _write_summary_block(self, worksheet, formats, start_row, start_col, federation_total_cell, sports_total_cell, specialized_total_cell, chess_total_cell):
        worksheet.merge_range(start_row, start_col, start_row, start_col + 2, 'اجمالي الربط المالي للجهات الرياضية', formats['section'])
        headers = ['م', 'الجهة', 'الدعم السنوي']
        for offset, header in enumerate(headers):
            worksheet.write(start_row + 1, start_col + offset, header, formats['header'])

        rows = [
            ('الاتحادات', federation_total_cell),
            ('الأندية الرياضية', sports_total_cell),
            ('الأندية المتخصصة', specialized_total_cell),
            ('أندية لعبة الشطرنج', chess_total_cell),
        ]
        row = start_row + 2
        for sequence, (label, formula_cell) in enumerate(rows, start=1):
            worksheet.write(row, start_col, sequence, formats['integer'])
            worksheet.write(row, start_col + 1, label, formats['text'])
            worksheet.write_formula(row, start_col + 2, f'={formula_cell}', formats['number'])
            row += 1

        worksheet.merge_range(row, start_col, row, start_col + 1, 'الإجمالي', formats['total_text'])
        first = xlsxwriter.utility.xl_rowcol_to_cell(start_row + 2, start_col + 2)
        last = xlsxwriter.utility.xl_rowcol_to_cell(row - 1, start_col + 2)
        worksheet.write_formula(row, start_col + 2, f'=SUM({first}:{last})', formats['total'])

    def _write_detail_sheet(self, workbook, formats, data):
        worksheet = workbook.add_worksheet('تفاصيل الطلبات')
        worksheet.freeze_panes(1, 0)
        headers = [
            'Reference',
            'Federation',
            'Support Item',
            'Code',
            'Category',
            'Status',
            'Requested',
            'Eligible',
            'Approved',
            'Net Payable',
            'Report Line',
        ]
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, formats['detail_header'])
        for row, detail in enumerate(data['request_details'], start=1):
            worksheet.write(row, 0, detail['reference'], formats['detail_text'])
            worksheet.write(row, 1, detail['federation'], formats['detail_text'])
            worksheet.write(row, 2, detail['support_item'], formats['detail_text'])
            worksheet.write(row, 3, detail['support_code'], formats['detail_text'])
            worksheet.write(row, 4, detail['category'], formats['detail_text'])
            worksheet.write(row, 5, detail['state'], formats['detail_text'])
            worksheet.write(row, 6, detail['requested_amount'], formats['detail_number'])
            worksheet.write(row, 7, detail['eligible_amount'], formats['detail_number'])
            worksheet.write(row, 8, detail['approved_amount'], formats['detail_number'])
            worksheet.write(row, 9, detail['net_payable'], formats['detail_number'])
            worksheet.write(row, 10, detail['report_line'], formats['detail_text'])
        widths = [18, 34, 34, 16, 22, 18, 16, 16, 16, 16, 20]
        for col, width in enumerate(widths):
            worksheet.set_column(col, col, width)

    def _build_workbook(self, data):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        formats = self._formats(workbook)
        worksheet = workbook.add_worksheet(f"اجمالى الدعم المالى {data['fiscal_year']}")
        worksheet.right_to_left()
        worksheet.set_landscape()
        worksheet.fit_to_pages(1, 0)
        worksheet.freeze_panes(2, 0)

        widths = [6, 34, 13, 14, 14, 14, 14, 14, 14, 14, 14, 16, 16, 14, 14, 14, 14, 16]
        for col, width in enumerate(widths):
            worksheet.set_column(col, col, width)
        worksheet.set_column(19, 24, 16)
        worksheet.set_column(26, 29, 16)
        worksheet.set_column(31, 34, 16)
        worksheet.set_column(36, 38, 18)

        federation_total_row = self._write_federation_block(worksheet, formats, data) - 2
        sports_total_row = self._write_club_block(
            worksheet,
            formats,
            0,
            19,
            f"الأندية الرياضية {data['fiscal_year']}",
            data['sports_clubs'],
            ['م', 'اسم النادي', 'الدعم الإداري', 'دعم الألعاب', 'الإعانة الشهرية', 'الإعانة السنوية'],
        )
        specialized_total_row = self._write_club_block(
            worksheet,
            formats,
            0,
            26,
            f"الأندية المتخصصة {data['fiscal_year']}",
            data['specialized_clubs'],
            ['م', 'الأندية التخصصية', 'الإعانة الشهرية', 'الدعم السنوي'],
        )
        chess_total_row = self._write_club_block(
            worksheet,
            formats,
            0,
            31,
            f"أندية لعبة الشطرنج {data['fiscal_year']}",
            data['chess_clubs'],
            ['م', 'أندية لعبة الشطرنج', 'الإعانة الشهرية', 'الدعم السنوي'],
        )
        self._write_summary_block(
            worksheet,
            formats,
            0,
            36,
            xlsxwriter.utility.xl_rowcol_to_cell(federation_total_row, 17),
            xlsxwriter.utility.xl_rowcol_to_cell(sports_total_row, 24),
            xlsxwriter.utility.xl_rowcol_to_cell(specialized_total_row, 29),
            xlsxwriter.utility.xl_rowcol_to_cell(chess_total_row, 34),
        )

        note_row = max(federation_total_row + 3, sports_total_row + 3, specialized_total_row + 3, chess_total_row + 3)
        worksheet.merge_range(
            note_row,
            0,
            note_row,
            17,
            'تم إنشاء هذا التقرير من طلبات الدعم المعتمدة أو اللاحقة للاعتماد. تفاصيل الطلبات في الورقة الثانية.',
            formats['total_text'],
        )
        worksheet.write(note_row + 1, 0, 'تاريخ الإنشاء', formats['header'])
        worksheet.merge_range(note_row + 1, 1, note_row + 1, 3, data['generated_on'].strftime('%Y-%m-%d %H:%M'), formats['text'])

        self._write_detail_sheet(workbook, formats, data)
        workbook.close()
        output.seek(0)
        return output.getvalue()

    @http.route('/ministry/reports/financial-support/entities-clubs.xlsx', type='http', auth='user')
    def financial_support_entities_clubs_xlsx(self, fiscal_year=None, **kwargs):
        self._require_report_access()
        fiscal_year = self._fiscal_year(fiscal_year)
        data = self._collect_report_data(fiscal_year)
        content = self._build_workbook(data)
        filename = f'الدعم المالى للجهات الرياضية والاندية نهائي {fiscal_year}.xlsx'
        headers = [
            ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ('Content-Length', str(len(content))),
            ('Content-Disposition', content_disposition(filename)),
            ('X-Content-Type-Options', 'nosniff'),
        ]
        return request.make_response(content, headers=headers)
