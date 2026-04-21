from odoo import http
from odoo.http import content_disposition, request


class PalletTsplController(http.Controller):
    @http.route('/manufacturing_pallet_barcode/tspl', type='http', auth='user', methods=['GET'])
    def download_tspl(self, ids=None, **kwargs):
        package_ids = []
        if ids:
            package_ids = [int(x) for x in ids.split(',') if x.strip().isdigit()]
        packages = request.env['stock.package'].browse(package_ids).exists()
        if not packages:
            return request.not_found()

        payload = packages._build_tspl_payload()
        filename = 'pallet_labels_%s.tspl' % request.env.company.id
        return request.make_response(
            payload,
            headers=[
                ('Content-Type', 'text/plain; charset=utf-8'),
                ('Content-Disposition', content_disposition(filename)),
            ],
        )
