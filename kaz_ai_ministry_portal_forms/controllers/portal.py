# -*- coding: utf-8 -*-
import mimetypes
import os
from datetime import timedelta

from werkzeug.exceptions import Forbidden, NotFound

from odoo import _, fields, http
from odoo.exceptions import ValidationError
from odoo.http import content_disposition, request
from odoo.tools.misc import file_path
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class MinistryPortal(CustomerPortal):
    """Portal routes for federation self-service forms."""

    _participation_levels = {'local', 'arab', 'regional', 'asian', 'international', 'olympic'}
    _hosting_levels = {'local', 'arab', 'regional', 'asian', 'international'}
    _participation_categories = {'men', 'women', 'youth', 'mixed'}
    _report_levels = {'local', 'arab', 'regional', 'asian', 'international', 'olympic'}
    _download_file_extensions = ('.pdf', '.doc', '.docx', '.xls', '.xlsx', '.png')

    def _prepare_home_portal_values(self, counters):
        """Add ministry counters to the portal home page."""
        values = super()._prepare_home_portal_values(counters)
        federation = self._get_current_federation()
        if not federation:
            return values

        domain = [('federation_id', '=', federation.id)]
        if 'participation_count' in counters:
            values['participation_count'] = request.env[
                'ministry.championship.participation'
            ].sudo().search_count(domain)
        if 'hosting_count' in counters:
            values['hosting_count'] = request.env[
                'ministry.championship.hosting'
            ].sudo().search_count(domain)
        if 'report_count' in counters:
            values['report_count'] = request.env[
                'ministry.post.event.report'
            ].sudo().search_count(domain)
        return values

    def _get_current_federation(self):
        """Return the federation partner for the logged-in portal user."""
        partner = request.env.user.partner_id
        if partner.is_federation:
            return partner
        if partner.parent_id.is_federation:
            return partner.parent_id
        if partner.commercial_partner_id.is_federation:
            return partner.commercial_partner_id
        return request.env['res.partner']

    def _require_current_federation(self):
        if not request.env.user.has_group('kaz_ai_ministry_branding.group_ministry_portal'):
            raise Forbidden(_('Your user is not configured for federation portal access.'))
        federation = self._get_current_federation()
        if not federation:
            raise Forbidden(_('Your portal user is not linked to a federation.'))
        return federation

    def _get_federation_domain(self):
        """Return domain restricting records to the current user's federation."""
        federation = self._require_current_federation()
        return [('federation_id', '=', federation.id)]

    def _get_download_forms(self):
        document_description = _('Official Ministry document from the forms and reports package.')
        return [
            {
                'key': 'gov_document_0848',
                'title': '0848 (3)',
                'description': document_description,
                'filename': '0848 (3).pdf',
                'path': ('data', 'download_forms', 'gov_document_0848.pdf'),
                'file_label': 'PDF',
                'icon_class': 'fa-file-pdf-o',
            },
            {
                'key': 'financial_support_sports_entities_clubs_2026',
                'title': 'الدعم المالى للجهات الرياضية والاندية نهائي 2026',
                'description': _('Financial support spreadsheet for sports entities and clubs.'),
                'filename': '1الدعم المالى للجهات الرياضية والاندية نهائي 2026.xlsx',
                'path': ('data', 'download_forms', 'financial_support_sports_entities_clubs_2026.xlsx'),
                'file_label': 'XLSX',
                'icon_class': 'fa-file-excel-o',
            },
            {
                'key': 'uae_mos_en',
                'title': 'UAE Ministry of Sports Logo',
                'description': _('Official Ministry logo image included with the reference package.'),
                'filename': 'UAE_MOS_EN.png',
                'path': ('data', 'download_forms', 'uae_mos_en.png'),
                'file_label': 'PNG',
                'icon_class': 'fa-file-image-o',
            },
            {
                'key': 'external_championship_form_11',
                'title': 'استمارة 11 بطولة خارجية',
                'description': _('External championship form.'),
                'filename': 'استمارة 11بطولة خارجية.pdf',
                'path': ('data', 'download_forms', 'external_championship_form_11.pdf'),
                'file_label': 'PDF',
                'icon_class': 'fa-file-pdf-o',
            },
            {
                'key': 'external_championship_hosting_application',
                'title': 'استمارة استضافة بطولة خارجية',
                'description': _('External championship hosting application form.'),
                'filename': 'استمارة استضافة بطولة خارجية.doc',
                'path': ('data', 'download_forms', 'external_championship_hosting_application.doc'),
                'file_label': 'DOC',
                'icon_class': 'fa-file-word-o',
            },
            {
                'key': 'sports_championship_participation_application',
                'title': 'استمارة المشاركة في البطولات الرياضية',
                'description': _('Sports championship participation application form.'),
                'filename': 'استمارة المشاركة في البطولات الرياضية.doc',
                'path': ('data', 'download_forms', 'sports_championship_participation_application.doc'),
                'file_label': 'DOC',
                'icon_class': 'fa-file-word-o',
            },
            {
                'key': 'participation_application_1111_doc',
                'title': 'استمارة المشاركة 1111',
                'description': _('Participation application form.'),
                'filename': 'استمارة المشاركة1111.doc',
                'path': ('data', 'download_forms', 'participation_application_1111.doc'),
                'file_label': 'DOC',
                'icon_class': 'fa-file-word-o',
            },
            {
                'key': 'participation_application_1111_pdf',
                'title': 'استمارة المشاركة 1111',
                'description': _('Participation application form.'),
                'filename': 'استمارة المشاركة1111.pdf',
                'path': ('data', 'download_forms', 'participation_application_1111.pdf'),
                'file_label': 'PDF',
                'icon_class': 'fa-file-pdf-o',
            },
            {
                'key': 'actual_disbursement',
                'title': 'الصرف الفعلي',
                'description': _('Actual disbursement report.'),
                'filename': 'الصرف الفعلي.pdf',
                'path': ('data', 'download_forms', 'actual_disbursement.pdf'),
                'file_label': 'PDF',
                'icon_class': 'fa-file-pdf-o',
            },
            {
                'key': 'external_championship_participation_report_doc',
                'title': 'تقرير عن المشاركة في البطولات الخارجية',
                'description': _('External championship participation report form.'),
                'filename': 'تقرير عن المشاركة في البطولات الخارجية.doc',
                'path': ('data', 'download_forms', 'external_championship_participation_report.doc'),
                'file_label': 'DOC',
                'icon_class': 'fa-file-word-o',
            },
            {
                'key': 'external_championship_participation_report',
                'title': 'تقرير عن المشاركة في البطولات الخارجية',
                'description': _('External championship participation report form.'),
                'filename': 'تقرير عن المشاركة في البطولات الخارجية.pdf',
                'path': ('data', 'download_forms', 'external_championship_participation_report.pdf'),
                'file_label': 'PDF',
                'icon_class': 'fa-file-pdf-o',
            },
            {
                'key': 'request_receipt_method',
                'title': 'طريقة استلام الطلب',
                'description': _('Request receipt method reference document.'),
                'filename': 'طريقة استلام الطلب.pdf',
                'path': ('data', 'download_forms', 'request_receipt_method.pdf'),
                'file_label': 'PDF',
                'icon_class': 'fa-file-pdf-o',
            },
            {
                'key': 'system_development_project',
                'title': 'مشروع تطوير النظام',
                'description': _('System development project reference document.'),
                'filename': 'مشروع تطوير النظام.pdf',
                'path': ('data', 'download_forms', 'system_development_project.pdf'),
                'file_label': 'PDF',
                'icon_class': 'fa-file-pdf-o',
            },
            {
                'key': 'financial_support_system_development_project',
                'title': 'مشروع تطوير نظام إدارة الدعم المالي للاتحادات الرياضية',
                'description': _('Financial support system development project reference document.'),
                'filename': 'مشروع تطوير نظام إدارة الدعم المالي للاتحادات الرياضية.pdf',
                'path': ('data', 'download_forms', 'financial_support_system_development_project.pdf'),
                'file_label': 'PDF',
                'icon_class': 'fa-file-pdf-o',
            },
        ]

    def _get_download_form(self, form_key):
        for download_form in self._get_download_forms():
            if download_form['key'] == form_key:
                return download_form
        return False

    def _require_download_access(self):
        if request.env.user.has_group('base.group_user'):
            return True
        self._require_current_federation()
        return True

    def _get_open_report_requests(self, federation):
        return request.env['ministry.support.request'].sudo().search([
            ('federation_id', '=', federation.id),
            ('state', '=', 'awaiting_report'),
        ], order='create_date desc')

    def _participation_budget_templates(self):
        return [
            {
                'key': 'fees_registration',
                'sequence': 10,
                'expense_group': 'fees',
                'group_label': _('Fees'),
                'description': _('Full delegation registration fees'),
                'default_quantity': 1,
            },
            {
                'key': 'tickets_administrators',
                'sequence': 20,
                'expense_group': 'travel_tickets',
                'group_label': _('Travel Tickets'),
                'description': _('Administrators'),
                'default_quantity': 0,
            },
            {
                'key': 'tickets_coaches',
                'sequence': 30,
                'expense_group': 'travel_tickets',
                'group_label': _('Travel Tickets'),
                'description': _('Coaches'),
                'default_quantity': 0,
            },
            {
                'key': 'tickets_players',
                'sequence': 40,
                'expense_group': 'travel_tickets',
                'group_label': _('Travel Tickets'),
                'description': _('Players'),
                'default_quantity': 0,
            },
            {
                'key': 'accommodation_administrators',
                'sequence': 50,
                'expense_group': 'accommodation_meals',
                'group_label': _('Accommodation and Meals'),
                'description': _('Administrators'),
                'default_quantity': 0,
            },
            {
                'key': 'accommodation_coaches',
                'sequence': 60,
                'expense_group': 'accommodation_meals',
                'group_label': _('Accommodation and Meals'),
                'description': _('Coaches'),
                'default_quantity': 0,
            },
            {
                'key': 'accommodation_players',
                'sequence': 70,
                'expense_group': 'accommodation_meals',
                'group_label': _('Accommodation and Meals'),
                'description': _('Players'),
                'default_quantity': 0,
            },
            {
                'key': 'pocket_administrators',
                'sequence': 80,
                'expense_group': 'pocket_money',
                'group_label': _('Pocket Money'),
                'description': _('Administrators'),
                'default_quantity': 0,
            },
            {
                'key': 'pocket_coaches',
                'sequence': 90,
                'expense_group': 'pocket_money',
                'group_label': _('Pocket Money'),
                'description': _('Coaches'),
                'default_quantity': 0,
            },
            {
                'key': 'pocket_players',
                'sequence': 100,
                'expense_group': 'pocket_money',
                'group_label': _('Pocket Money'),
                'description': _('Players'),
                'default_quantity': 0,
            },
            {
                'key': 'other_sportswear',
                'sequence': 110,
                'expense_group': 'other_expenses',
                'group_label': _('Other Expenses'),
                'description': _('Sportswear, two sets per person'),
                'default_quantity': 0,
            },
            {
                'key': 'other_reserve_team',
                'sequence': 120,
                'expense_group': 'other_expenses',
                'group_label': _('Other Expenses'),
                'description': _('Reserve team expenses'),
                'default_quantity': 1,
            },
        ]

    def _get_participation_budget_values(self, values=None):
        values = values or {}
        budget_lines = []
        for template in self._participation_budget_templates():
            key = template['key']
            quantity = values.get(f'budget_quantity_{key}', template['default_quantity'])
            unit_amount = values.get(f'budget_unit_amount_{key}', '')
            try:
                total_amount = float(quantity or 0.0) * float(unit_amount or 0.0)
            except (TypeError, ValueError):
                total_amount = 0.0
            budget_lines.append({
                **template,
                'quantity_value': quantity,
                'unit_amount_value': unit_amount,
                'total_amount': total_amount,
            })
        return budget_lines

    def _render_participation_form(self, errors=None, values=None):
        budget_lines = self._get_participation_budget_values(values)
        return request.render('kaz_ai_ministry_portal_forms.portal_participation_form', {
            'page_name': 'participation',
            'error': errors or {},
            'values': values or {},
            'budget_lines': budget_lines,
            'budget_total': sum(line['total_amount'] for line in budget_lines),
        })

    def _render_hosting_form(self, errors=None, values=None):
        return request.render('kaz_ai_ministry_portal_forms.portal_hosting_form', {
            'page_name': 'hosting',
            'error': errors or {},
            'values': values or {},
        })

    def _render_report_form(self, federation, errors=None, values=None):
        return request.render('kaz_ai_ministry_portal_forms.portal_report_form', {
            'page_name': 'report',
            'open_requests': self._get_open_report_requests(federation),
            'error': errors or {},
            'values': values or {},
        })

    def _exception_message(self, exception):
        return exception.args[0] if exception.args else str(exception)

    def _required_text(self, post, field_name, errors):
        value = (post.get(field_name) or '').strip()
        if not value:
            errors[field_name] = _('This field is required.')
        return value

    def _parse_date(self, post, field_name, errors, required=False):
        value = post.get(field_name)
        if not value:
            if required:
                errors[field_name] = _('This field is required.')
            return False
        try:
            return fields.Date.to_date(value)
        except (TypeError, ValueError):
            errors[field_name] = _('Enter a valid date.')
            return False

    def _parse_int(self, post, field_name, errors, required=False, min_value=None, default=0):
        value = post.get(field_name)
        if value in (None, ''):
            if required:
                errors[field_name] = _('This field is required.')
            return default
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            errors[field_name] = _('Enter a valid whole number.')
            return default
        if min_value is not None and parsed < min_value:
            errors[field_name] = _('Value must be at least %(minimum)s.', minimum=min_value)
        return parsed

    def _parse_float(self, post, field_name, errors, required=False, min_value=None, default=0.0):
        value = post.get(field_name)
        if value in (None, ''):
            if required:
                errors[field_name] = _('This field is required.')
            return default
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            errors[field_name] = _('Enter a valid number.')
            return default
        if min_value is not None and parsed < min_value:
            errors[field_name] = _('Value must be at least %(minimum)s.', minimum=min_value)
        return parsed

    # Dashboard

    @http.route('/my/federation/dashboard', type='http', auth='user', website=True)
    def portal_dashboard(self, **kwargs):
        """Federation portal dashboard."""
        federation = self._require_current_federation()
        domain = [('federation_id', '=', federation.id)]

        participations = request.env['ministry.championship.participation'].sudo().search(
            domain, order='create_date desc', limit=5
        )
        hostings = request.env['ministry.championship.hosting'].sudo().search(
            domain, order='create_date desc', limit=5
        )
        reports = request.env['ministry.post.event.report'].sudo().search(
            domain, order='create_date desc', limit=5
        )
        support_requests = request.env['ministry.support.request'].sudo().search(
            domain, order='create_date desc', limit=5
        )

        return request.render('kaz_ai_ministry_portal_forms.portal_dashboard', {
            'federation': federation,
            'participations': participations,
            'hostings': hostings,
            'reports': reports,
            'support_requests': support_requests,
            'page_name': 'dashboard',
        })

    # Downloadable Forms

    @http.route('/my/championships/downloads', type='http', auth='user', website=True)
    def portal_download_forms(self, **kwargs):
        self._require_download_access()
        return request.render('kaz_ai_ministry_portal_forms.portal_download_forms', {
            'download_forms': self._get_download_forms(),
            'page_name': 'download_forms',
        })

    @http.route('/my/championships/downloads/<string:form_key>', type='http', auth='user', website=True)
    def portal_download_form_file(self, form_key, **kwargs):
        self._require_download_access()
        download_form = self._get_download_form(form_key)
        if not download_form:
            raise NotFound()

        try:
            download_path = file_path(
                '/'.join(('kaz_ai_ministry_portal_forms', *download_form['path'])),
                filter_ext=self._download_file_extensions,
                env=request.env,
            )
        except (FileNotFoundError, ValueError):
            raise NotFound()
        if not os.path.isfile(download_path):
            raise NotFound()

        with open(download_path, 'rb') as download_file:
            data = download_file.read()

        headers = [
            ('Content-Type', mimetypes.guess_type(download_form['filename'])[0] or 'application/octet-stream'),
            ('Content-Length', str(len(data))),
            ('Content-Disposition', content_disposition(download_form['filename'])),
            ('X-Content-Type-Options', 'nosniff'),
        ]
        return request.make_response(data, headers=headers)

    # Championship Participation

    @http.route([
        '/my/championships/participation',
        '/my/championships/participation/page/<int:page>',
    ], type='http', auth='user', website=True)
    def portal_participation_list(self, page=1, **kwargs):
        """List all participation applications for the current federation."""
        domain = self._get_federation_domain()
        Participation = request.env['ministry.championship.participation'].sudo()
        total = Participation.search_count(domain)
        pager = portal_pager(
            url='/my/championships/participation',
            total=total,
            page=page,
            step=10,
        )
        records = Participation.search(
            domain, order='create_date desc',
            limit=10, offset=pager['offset']
        )
        return request.render('kaz_ai_ministry_portal_forms.portal_participation_list', {
            'records': records,
            'pager': pager,
            'page_name': 'participation',
        })

    @http.route('/my/championships/participation/new', type='http', auth='user', website=True)
    def portal_participation_new(self, **kwargs):
        """Display the new participation application form."""
        self._require_current_federation()
        return self._render_participation_form()

    @http.route('/my/championships/participation/submit', type='http', auth='user', website=True,
                methods=['POST'], csrf=True)
    def portal_participation_submit(self, **post):
        """Handle participation form submission."""
        federation = self._require_current_federation()
        errors, vals = self._validate_participation(post)
        if errors:
            return self._render_participation_form(errors, post)

        try:
            with request.env.cr.savepoint():
                record = request.env['ministry.championship.participation'].sudo().create({
                    'federation_id': federation.id,
                    **vals,
                })
                record.sudo().action_submit()
        except ValidationError as error:
            errors['_global'] = self._exception_message(error)
            return self._render_participation_form(errors, post)

        return request.redirect('/my/championships/participation?submitted=1')

    def _validate_participation(self, post):
        errors = {}
        start = self._parse_date(post, 'event_date_start', errors, required=True)
        end = self._parse_date(post, 'event_date_end', errors, required=True)
        level = self._required_text(post, 'championship_level', errors)

        if level and level not in self._participation_levels:
            errors['championship_level'] = _('Select a valid championship level.')
        if start and end and end < start:
            errors['event_date_end'] = _('Event end date must be after start date.')
        if start and fields.Date.today() > (start - timedelta(days=15)):
            errors['event_date_start'] = _(
                'Applications must be submitted at least 15 days before the event start date.'
            )

        participation_category = (post.get('participation_category') or '').strip() or False
        if participation_category and participation_category not in self._participation_categories:
            errors['participation_category'] = _('Select a valid participation category.')

        budget_lines, budget_total = self._validate_participation_budget(post, errors)

        vals = {
            'championship_name': self._required_text(post, 'championship_name', errors),
            'championship_level': level,
            'event_date_start': start,
            'event_date_end': end,
            'location': self._required_text(post, 'location', errors),
            'athletes_count': self._parse_int(
                post, 'athletes_count', errors, required=True, min_value=1
            ),
            'officials_count': self._parse_int(post, 'officials_count', errors, min_value=0),
            'estimated_budget': budget_total,
            'budget_line_ids': [(0, 0, budget_line) for budget_line in budget_lines],
            'notes': (post.get('notes') or '').strip(),
            'sport_type': (post.get('sport_type') or '').strip(),
            'participation_category': participation_category,
            'countries_count': self._parse_int(post, 'countries_count', errors, min_value=0),
        }
        return errors, vals

    def _validate_participation_budget(self, post, errors):
        budget_lines = []
        budget_total = 0.0
        for template in self._participation_budget_templates():
            key = template['key']
            quantity = self._parse_float(
                post, f'budget_quantity_{key}', errors, min_value=0.0, default=0.0
            )
            unit_amount = self._parse_float(
                post, f'budget_unit_amount_{key}', errors, min_value=0.0, default=0.0
            )
            if unit_amount <= 0.0:
                continue
            if quantity <= 0.0:
                errors[f'budget_quantity_{key}'] = _(
                    'Enter a quantity greater than zero for each budget line with an amount.'
                )
                continue
            total_amount = quantity * unit_amount
            budget_total += total_amount
            budget_lines.append({
                'sequence': template['sequence'],
                'expense_group': template['expense_group'],
                'description': template['description'],
                'quantity': quantity,
                'unit_amount': unit_amount,
            })
        if not budget_lines:
            errors['budget_lines'] = _('Enter at least one estimated budget line.')
        return budget_lines, budget_total

    # Championship Hosting

    @http.route([
        '/my/championships/hosting',
        '/my/championships/hosting/page/<int:page>',
    ], type='http', auth='user', website=True)
    def portal_hosting_list(self, page=1, **kwargs):
        """List all hosting applications for the current federation."""
        domain = self._get_federation_domain()
        Hosting = request.env['ministry.championship.hosting'].sudo()
        total = Hosting.search_count(domain)
        pager = portal_pager(
            url='/my/championships/hosting',
            total=total,
            page=page,
            step=10,
        )
        records = Hosting.search(
            domain, order='create_date desc',
            limit=10, offset=pager['offset']
        )
        return request.render('kaz_ai_ministry_portal_forms.portal_hosting_list', {
            'records': records,
            'pager': pager,
            'page_name': 'hosting',
        })

    @http.route('/my/championships/hosting/new', type='http', auth='user', website=True)
    def portal_hosting_new(self, **kwargs):
        """Display the new hosting application form."""
        self._require_current_federation()
        return self._render_hosting_form()

    @http.route('/my/championships/hosting/submit', type='http', auth='user', website=True,
                methods=['POST'], csrf=True)
    def portal_hosting_submit(self, **post):
        """Handle hosting form submission."""
        federation = self._require_current_federation()
        errors, vals = self._validate_hosting(post)
        if errors:
            return self._render_hosting_form(errors, post)

        try:
            with request.env.cr.savepoint():
                record = request.env['ministry.championship.hosting'].sudo().create({
                    'federation_id': federation.id,
                    **vals,
                })
                record.sudo().action_submit()
        except ValidationError as error:
            errors['_global'] = self._exception_message(error)
            return self._render_hosting_form(errors, post)

        return request.redirect('/my/championships/hosting?submitted=1')

    def _validate_hosting(self, post):
        errors = {}
        start = self._parse_date(post, 'event_date_start', errors, required=True)
        end = self._parse_date(post, 'event_date_end', errors, required=True)
        level = self._required_text(post, 'championship_level', errors)

        if level and level not in self._hosting_levels:
            errors['championship_level'] = _('Select a valid championship level.')
        if start and end and end < start:
            errors['event_date_end'] = _('Event end date must be after start date.')
        if start and fields.Date.today() > (start - timedelta(days=30)):
            errors['event_date_start'] = _(
                'Hosting applications must be submitted at least 30 days before the event start date.'
            )

        vals = {
            'championship_name': self._required_text(post, 'championship_name', errors),
            'championship_level': level,
            'event_date_start': start,
            'event_date_end': end,
            'venue': self._required_text(post, 'venue', errors),
            'expected_participants': self._parse_int(
                post, 'expected_participants', errors, required=True, min_value=1
            ),
            'expected_countries': self._parse_int(
                post, 'expected_countries', errors, min_value=1, default=1
            ),
            'venue_capacity': self._parse_int(post, 'venue_capacity', errors, min_value=0),
            'hosting_budget': self._parse_float(
                post, 'hosting_budget', errors, required=True, min_value=0.0
            ),
            'notes': (post.get('notes') or '').strip(),
            'sport_type': (post.get('sport_type') or '').strip(),
            'organizer': (post.get('organizer') or '').strip(),
            'participant_categories': (post.get('participant_categories') or '').strip(),
            'funding_sources': (post.get('funding_sources') or '').strip(),
            'expected_return': (post.get('expected_return') or '').strip(),
        }
        return errors, vals

    # Post-Event Reports

    @http.route([
        '/my/championships/post-event-report',
        '/my/championships/post-event-report/page/<int:page>',
    ], type='http', auth='user', website=True)
    def portal_report_list(self, page=1, **kwargs):
        """List all post-event reports for the current federation."""
        domain = self._get_federation_domain()
        Report = request.env['ministry.post.event.report'].sudo()
        total = Report.search_count(domain)
        pager = portal_pager(
            url='/my/championships/post-event-report',
            total=total,
            page=page,
            step=10,
        )
        records = Report.search(
            domain, order='create_date desc',
            limit=10, offset=pager['offset']
        )
        return request.render('kaz_ai_ministry_portal_forms.portal_report_list', {
            'records': records,
            'pager': pager,
            'page_name': 'report',
        })

    @http.route('/my/championships/post-event-report/new', type='http', auth='user', website=True)
    def portal_report_new(self, **kwargs):
        """Display the new post-event report form."""
        federation = self._require_current_federation()
        return self._render_report_form(federation)

    @http.route('/my/championships/post-event-report/submit', type='http', auth='user', website=True,
                methods=['POST'], csrf=True)
    def portal_report_submit(self, **post):
        """Handle post-event report form submission."""
        federation = self._require_current_federation()
        errors, vals = self._validate_report(post, federation)
        if errors:
            return self._render_report_form(federation, errors, post)

        try:
            with request.env.cr.savepoint():
                record = request.env['ministry.post.event.report'].sudo().create({
                    'federation_id': federation.id,
                    **vals,
                })
                record.sudo().action_submit()
        except ValidationError as error:
            errors['_global'] = self._exception_message(error)
            return self._render_report_form(federation, errors, post)

        return request.redirect('/my/championships/post-event-report?submitted=1')

    def _validate_report(self, post, federation):
        errors = {}
        start = self._parse_date(post, 'event_date_start', errors, required=True)
        end = self._parse_date(post, 'event_date_end', errors, required=True)
        if start and end and end < start:
            errors['event_date_end'] = _('Event end date must be after start date.')

        support_request_id = False
        raw_support_request_id = post.get('support_request_id')
        if raw_support_request_id:
            try:
                support_request_id = int(raw_support_request_id)
            except (TypeError, ValueError):
                errors['support_request_id'] = _('Select a valid support request.')
            else:
                support_request = request.env['ministry.support.request'].sudo().search([
                    ('id', '=', support_request_id),
                    ('federation_id', '=', federation.id),
                    ('state', '=', 'awaiting_report'),
                ], limit=1)
                if not support_request:
                    errors['support_request_id'] = _(
                        'Select an awaiting-report support request for your federation.'
                    )

        achievement_pct = self._parse_float(post, 'achievement_pct', errors, min_value=0.0)
        if achievement_pct > 100:
            errors['achievement_pct'] = _('Achievement must be between 0 and 100.')

        report_level = (post.get('championship_level') or '').strip() or False
        if report_level and report_level not in self._report_levels:
            errors['championship_level'] = _('Select a valid championship level.')

        vals = {
            'event_name': self._required_text(post, 'event_name', errors),
            'event_date_start': start,
            'event_date_end': end,
            'athletes_participated': self._parse_int(
                post, 'athletes_participated', errors, required=True, min_value=1
            ),
            'medals_gold': self._parse_int(post, 'medals_gold', errors, min_value=0),
            'medals_silver': self._parse_int(post, 'medals_silver', errors, min_value=0),
            'medals_bronze': self._parse_int(post, 'medals_bronze', errors, min_value=0),
            'final_rank': self._parse_int(post, 'final_rank', errors, min_value=1) or False,
            'achievement_pct': achievement_pct,
            'actual_expenditure': self._parse_float(
                post, 'actual_expenditure', errors, min_value=0.0
            ),
            'support_request_id': support_request_id,
            'narrative': post.get('narrative') or '',
            'sport_type': (post.get('sport_type') or '').strip(),
            'championship_level': report_level,
            'event_location': (post.get('event_location') or '').strip(),
            'countries_count': self._parse_int(post, 'countries_count', errors, min_value=0),
            'goals_achieved': (post.get('goals_achieved') or '').strip(),
            'challenges': (post.get('challenges') or '').strip(),
            'recommendations': (post.get('recommendations') or '').strip(),
        }
        return errors, vals
