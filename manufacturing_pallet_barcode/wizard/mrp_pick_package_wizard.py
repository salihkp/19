import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MrpPickPackageWizard(models.TransientModel):
    _name = 'mrp.pick.package.wizard'
    _description = 'Wizard to Pick Multiple Packages for MO'

    production_id = fields.Many2one(
        'mrp.production', string='Manufacturing Order', required=True,
    )
    package_ids = fields.Many2many(
        'stock.package',
        string='Selected Packages',
        domain="[('location_id', 'child_of', parent_location_id)]",
    )

    parent_location_id = fields.Many2one(
        'stock.location',
        related='production_id.location_src_id',
        string='Source Location',
    )

    def action_confirm_picking(self):
        self.ensure_one()
        if not self.package_ids:
            raise UserError(_("Please select at least one package."))

        for package in self.package_ids:
            for quant in package.quant_ids:
                if quant.quantity <= 0:
                    continue

                # Find the matching raw move
                move = self.production_id.move_raw_ids.filtered(
                    lambda m, q=quant: m.product_id == q.product_id and m.state not in ('done', 'cancel')
                )
                if not move:
                    continue
                move = move[0]

                qty_to_pick = quant.quantity

                # Look for an existing unpicked line for this product/move
                unpicked_line = move.move_line_ids.filtered(
                    lambda l: not l.picked and not l.package_id
                )

                if unpicked_line:
                    line = unpicked_line[0]
                    if line.quantity <= qty_to_pick:
                        pick_qty = line.quantity
                        line.write({
                            'package_id': package.id,
                            'quantity': pick_qty,
                            'picked': True,
                        })
                        qty_to_pick -= pick_qty
                    else:
                        self.env['stock.move.line'].create({
                            'move_id': move.id,
                            'product_id': quant.product_id.id,
                            'quantity': qty_to_pick,
                            'product_uom_id': quant.product_uom_id.id,
                            'location_id': quant.location_id.id,
                            'location_dest_id': self.production_id.production_location_id.id,
                            'package_id': package.id,
                            'picked': True,
                        })
                        line.quantity -= qty_to_pick
                        qty_to_pick = 0

                # If there's still quantity to pick
                if qty_to_pick > 0:
                    self.env['stock.move.line'].create({
                        'move_id': move.id,
                        'product_id': quant.product_id.id,
                        'quantity': qty_to_pick,
                        'product_uom_id': quant.product_uom_id.id,
                        'location_id': quant.location_id.id,
                        'location_dest_id': self.production_id.production_location_id.id,
                        'package_id': package.id,
                        'picked': True,
                    })

        picked_count = len(self.package_ids)
        _logger.info(
            'MO %s: Picked %d packages via wizard.',
            self.production_id.name, picked_count,
        )

        self.production_id.message_post(
            body=_("Picked <b>%d</b> packages as raw material components.") % picked_count,
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )

        return {'type': 'ir.actions.act_window_close'}
