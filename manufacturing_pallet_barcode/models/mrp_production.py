import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    pallet_ids = fields.One2many(
        'stock.package',
        'production_id',
        string='Pallets',
    )

    pallet_count = fields.Integer(
        string='Pallet Count',
        compute='_compute_pallet_count',
        store=True,
    )

    is_sticker_stage = fields.Boolean(
        string='Sticker Stage?',
        compute='_compute_is_sticker_stage',
        store=True,
    )

    sticker_product_id = fields.Many2one(
        'product.product',
        string='Sticker Product',
        domain="[('type', '=', 'consu')]",
        help='The sticker consumed for this manufacturing order',
    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('pallet_ids')
    def _compute_pallet_count(self):
        for mo in self:
            mo.pallet_count = len(mo.pallet_ids)

    @api.depends('product_id', 'product_id.product_tmpl_id.needs_sticker', 'sticker_product_id')
    def _compute_is_sticker_stage(self):
        """Determine if this MO is for a product that needs stickers."""
        for mo in self:
            mo.is_sticker_stage = (
                mo.product_id.product_tmpl_id.needs_sticker
                or bool(mo.sticker_product_id)
            )

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------

    @api.onchange('sticker_product_id')
    def _onchange_sticker_product_id(self):
        if self.sticker_product_id:
            existing_move = self.move_raw_ids.filtered(
                lambda m: m.product_id == self.sticker_product_id
            )
            if not existing_move:
                self.move_raw_ids = [(0, 0, {
                    'product_id': self.sticker_product_id.id,
                    'product_uom_qty': 0.0,
                    'product_uom': self.sticker_product_id.uom_id.id,
                    'location_id': self.location_src_id.id,
                    'location_dest_id': self.production_location_id.id,
                    'description_picking': self.sticker_product_id.display_name,
                    'raw_material_production_id': self._origin.id or self.id,
                })]

    @api.onchange('product_id')
    def _onchange_product_id_sticker(self):
        if self.product_id:
            self.sticker_product_id = self.product_id.product_tmpl_id.sticker_product_id

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    def button_mark_done(self):
        res = super().button_mark_done()
        for mo in self:
            packages_to_pack = mo.pallet_ids.filtered(
                lambda p: p.target_qty > 0 and p.product_qty < p.target_qty
            )
            if packages_to_pack:
                mo._pack_missing_pallet_quantities(packages_to_pack)
                _logger.info(
                    'MO %s: Packed/updated %d pallets on mark done.',
                    mo.name, len(packages_to_pack),
                )
        return res

    def _pack_missing_pallet_quantities(self, packages):
        """Pack available produced quantity into given pallets.

        This supports partial manufacturing: pallets can receive quantities
        as soon as products are produced (qty_produced), not only when the
        MO reaches done state.
        """
        self.ensure_one()
        if not packages:
            return

        produced_remaining = max(
            float(self.qty_produced) - sum(self.pallet_ids.mapped('product_qty')),
            0.0,
        )
        if produced_remaining <= 0:
            return

        candidate_locations = [self.location_dest_id]
        if self.production_location_id and self.production_location_id != self.location_dest_id:
            candidate_locations.append(self.production_location_id)

        for package in packages:
            qty_missing = max(float(package.target_qty) - float(package.product_qty), 0.0)
            qty_to_pack = min(qty_missing, produced_remaining)
            if qty_to_pack <= 0:
                continue

            for location in candidate_locations:
                if qty_to_pack <= 0:
                    break
                packed_qty = package.pack_quants_from_production(
                    product=self.product_id,
                    location=location,
                    qty_to_pack=qty_to_pack,
                )
                qty_to_pack -= packed_qty
                produced_remaining -= packed_qty
                if produced_remaining <= 0:
                    return

    def action_create_pallet(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Pallet'),
            'res_model': 'mrp.pallet.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_production_id': self.id,
            },
        }

    def action_view_pallets(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pallets'),
            'res_model': 'stock.package',
            'view_mode': 'list,form',
            'domain': [('production_id', '=', self.id)],
        }

    def action_mark_sticker_applied(self):
        self.ensure_one()
        applied_count = 0
        sticker_product = (
            self.sticker_product_id
            or self.product_id.product_tmpl_id.sticker_product_id
        )

        if not sticker_product and self.is_sticker_stage:
            raise UserError(_(
                'Please configure a sticker product on the Manufacturing Order or Product Template.'
            ))

        for pallet in self.pallet_ids:
            if pallet.pallet_state == 'without_sticker':
                pallet.pallet_state = 'with_sticker'
                applied_count += 1

        if sticker_product and applied_count > 0:
            sticker_move = self.move_raw_ids.filtered(
                lambda m: m.product_id == sticker_product
            )
            if not sticker_move:
                sticker_move = self.env['stock.move'].create({
                    'product_id': sticker_product.id,
                    'product_uom_qty': 0.0,
                    'product_uom': sticker_product.uom_id.id,
                    'location_id': self.location_src_id.id,
                    'location_dest_id': self.production_location_id.id,
                    'description_picking': _('Sticker Consumption - %s') % self.name,
                    'raw_material_production_id': self.id,
                })

            new_qty = sticker_move.product_uom_qty + float(applied_count)
            sticker_move.write({'product_uom_qty': new_qty})

            if self.state == 'progress':
                sticker_move.picked = True
                sticker_move.quantity += float(applied_count)

            _logger.info(
                'MO %s: Applied stickers on %d pallets. Sticker consumption updated to %.2f.',
                self.name, applied_count, new_qty,
            )

        if applied_count > 0:
            self.message_post(
                body=_("Successfully applied stickers on <b>%d</b> pallets") % applied_count,
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )

    def action_pick_packages(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pick Packages for MO'),
            'res_model': 'mrp.pick.package.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_production_id': self.id,
            },
        }
