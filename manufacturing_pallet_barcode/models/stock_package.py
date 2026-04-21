import base64
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class StockPackage(models.Model):
    _inherit = 'stock.package'

    pallet_state = fields.Selection([
        ('without_sticker', 'Without Sticker'),
        ('with_sticker', 'With Sticker'),
    ], string='Pallet State', default='without_sticker')

    is_stickered = fields.Boolean(
        string='Stickered',
        help='Indicates whether the sticker has been physically applied to this pallet after printing',
    )

    target_qty = fields.Float(
        string='Target Quantity',
        help='The planned quantity for this pallet when created from the wizard.',
    )

    product_qty = fields.Float(
        string='Product Quantity',
        compute='_compute_product_qty',
        store=True,
    )
    pallet_qty = fields.Float(
        string='Pallet Quantity',
        compute='_compute_pallet_qty',
        store=True,
        help='Shown pallet quantity: actual packed quantity when available, '
             'otherwise planned target quantity.',
    )

    production_id = fields.Many2one(
        'mrp.production',
        string='Manufacturing Order',
    )

    barcode_display = fields.Char(
        string='Pallet Barcode',
        compute='_compute_barcode_display',
        store=True,
        help='Pallet Barcode - Changes based on sticker state',
    )
    barcode_image = fields.Binary(
        string='Barcode Image',
        compute='_compute_barcode_image',
        help='Rendered barcode image for report printing.',
    )
    barcode_image_src = fields.Char(
        string='Barcode Image Src',
        compute='_compute_barcode_image',
        help='Data URI source for barcode rendering in reports.',
    )

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        related='production_id.product_id',
        store=True,
        readonly=True,
    )

    mo_name = fields.Char(
        string='MO Name',
        related='production_id.name',
        store=True,
        readonly=True,
    )

    sale_order_ref = fields.Char(
        string='Sales Order',
        compute='_compute_sale_order_info',
    )

    sale_order_date = fields.Date(
        string='Sales Order Date',
        compute='_compute_sale_order_info',
    )

    # -------------------------------------------------------------------------
    # CONSTRAINTS
    # -------------------------------------------------------------------------

    @api.constrains('target_qty')
    def _check_target_qty(self):
        for pkg in self:
            if pkg.target_qty < 0:
                raise ValidationError(_('Target quantity cannot be negative.'))

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('quant_ids', 'quant_ids.quantity')
    def _compute_product_qty(self):
        for pkg in self:
            pkg.product_qty = sum(pkg.quant_ids.mapped('quantity'))

    @api.depends('product_qty', 'target_qty')
    def _compute_pallet_qty(self):
        for pkg in self:
            pkg.pallet_qty = pkg.product_qty if pkg.product_qty > 0 else pkg.target_qty

    @api.depends('name', 'pallet_state')
    def _compute_barcode_display(self):
        for pkg in self:
            if pkg.name:
                suffix = 'NS' if pkg.pallet_state == 'without_sticker' else 'WS'
                pkg.barcode_display = f"{pkg.name}-{suffix}"
            else:
                pkg.barcode_display = False

    @api.depends('barcode_display', 'name')
    def _compute_barcode_image(self):
        report_model = self.env['ir.actions.report']
        for pkg in self:
            value = pkg.barcode_display or pkg.name
            if not value:
                pkg.barcode_image = False
                pkg.barcode_image_src = False
                continue
            try:
                barcode_png = report_model.barcode(
                    barcode_type='Code128',
                    value=value,
                    width=600,
                    height=140,
                    humanreadable=0,
                    quiet=0,
                )
                barcode_b64 = base64.b64encode(barcode_png).decode()
                pkg.barcode_image = barcode_b64
                pkg.barcode_image_src = f"data:image/png;base64,{barcode_b64}"
            except Exception:
                _logger.exception('Failed to generate barcode image for package %s', pkg.id)
                pkg.barcode_image = False
                pkg.barcode_image_src = False

    def _compute_sale_order_info(self):
        """Resolve sales order reference/date for label printing.

        Priority:
        1) sale_mrp link (sale_line_id.order_id)
        2) sale_stock stock references (reference_ids.sale_ids)
        3) fallback by matching MO origin to SO name
        """
        sale_order_model_installed = 'sale.order' in self.env
        sale_order_model = self.env['sale.order'] if sale_order_model_installed else False

        for pkg in self:
            pkg.sale_order_ref = False
            pkg.sale_order_date = False
            production = pkg.production_id
            if not production:
                continue

            sale_order = False
            if 'sale_line_id' in production._fields and production.sale_line_id:
                sale_order = production.sale_line_id.order_id

            if not sale_order and 'reference_ids' in production._fields and production.reference_ids:
                references = production.reference_ids
                if 'sale_ids' in references._fields and references.sale_ids:
                    sale_order = references.sale_ids[:1]

            if not sale_order and sale_order_model:
                origin = (production.origin or '').split(',')[0].strip()
                if origin:
                    sale_order = sale_order_model.search([('name', '=', origin)], limit=1)

            if sale_order:
                pkg.sale_order_ref = sale_order.name
                pkg.sale_order_date = fields.Date.to_date(sale_order.date_order) if sale_order.date_order else False

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    def pack_quants_from_production(self, product, location, qty_to_pack):
        """Shared method: assign unpackaged quants to this package.

        This method is called from both the MO completion flow and the
        pallet creation wizard, eliminating duplicated quant-packing logic.

        :param product: product.product recordset
        :param location: stock.location recordset (destination)
        :param qty_to_pack: float quantity to pack into this package
        """
        self.ensure_one()
        if qty_to_pack <= 0:
            return 0.0
        quants = self.env['stock.quant'].search([
            ('product_id', '=', product.id),
            ('location_id', '=', location.id),
            ('package_id', '=', False),
            ('quantity', '>', 0),
        ])
        qty_needed = qty_to_pack
        for quant in quants:
            if qty_needed <= 0:
                break
            take_qty = min(quant.quantity, qty_needed)
            if take_qty == quant.quantity:
                quant.write({'package_id': self.id})
            else:
                self.env['stock.quant']._update_available_quantity(
                    product_id=product,
                    location_id=location,
                    quantity=-take_qty,
                )
                self.env['stock.quant']._update_available_quantity(
                    product_id=product,
                    location_id=location,
                    quantity=take_qty,
                    package_id=self,
                )
            qty_needed -= take_qty

        _logger.info(
            'Packed %.2f of %s into package %s (remaining unmet: %.2f)',
            qty_to_pack - qty_needed, product.display_name,
            self.name, max(qty_needed, 0),
        )
        return qty_to_pack - qty_needed

    def action_print_barcode(self):
        """Print barcode label from form (single) or list (multi)."""
        packages = self
        if not packages and self.env.context.get('active_model') == 'stock.package':
            packages = self.browse(self.env.context.get('active_ids', []))
        if not packages:
            raise UserError(_('Please select at least one pallet to print.'))
        return self.env.ref(
            'manufacturing_pallet_barcode.report_pallet_barcode'
        ).report_action(packages)
