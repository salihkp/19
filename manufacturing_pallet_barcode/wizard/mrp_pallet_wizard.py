import logging

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class MrpPalletWizard(models.TransientModel):
    _name = 'mrp.pallet.wizard'
    _description = 'Wizard to Create Pallet with Quantity'

    production_id = fields.Many2one(
        'mrp.production', string='Manufacturing Order', required=True,
    )
    product_id = fields.Many2one(
        'product.product', related='production_id.product_id', string='Product',
    )

    total_quantity = fields.Float(
        string='Total Quantity to Pack',
        required=True,
        default=0.0,
        help='Total quantity that will be distributed across pallets',
    )
    capacity_per_pallet = fields.Float(
        string='Capacity per Pallet',
        required=True,
        default=1000.0,
        help='Maximum quantity a single pallet can hold',
    )

    use_existing_package = fields.Boolean(string='Reuse Existing Package')
    location_dest_id = fields.Many2one(
        'stock.location', related='production_id.location_dest_id',
    )
    company_id = fields.Many2one(
        'res.company', related='production_id.company_id',
    )
    package_type_id = fields.Many2one(
        'stock.package.type',
        string='Package Type',
        domain="[('company_id', 'in', [False, company_id])]",
    )
    existing_package_id = fields.Many2one(
        'stock.package',
        string='Existing Package',
        domain="[('location_id', '=', location_dest_id)]",
    )

    # -------------------------------------------------------------------------
    # CONSTRAINTS
    # -------------------------------------------------------------------------

    @api.constrains('total_quantity', 'capacity_per_pallet')
    def _check_quantities(self):
        for wiz in self:
            if wiz.total_quantity <= 0:
                raise ValidationError(_('Total quantity must be greater than zero.'))
            if not wiz.use_existing_package and wiz.capacity_per_pallet <= 0:
                raise ValidationError(_('Capacity per pallet must be greater than zero.'))

    # -------------------------------------------------------------------------
    # ACTIONS
    # -------------------------------------------------------------------------

    def action_create_pallet(self):
        self.ensure_one()
        state = 'with_sticker' if self.production_id.is_sticker_stage else 'without_sticker'

        if self.use_existing_package and self.existing_package_id:
            package = self.existing_package_id
            package_vals = {
                'production_id': self.production_id.id,
                'pallet_state': state,
                'target_qty': self.total_quantity,
                'is_stickered': False,
            }
            if self.package_type_id:
                package_vals['package_type_id'] = self.package_type_id.id
            package.write(package_vals)
            created_packages = package
        else:
            remaining_qty = self.total_quantity
            created_packages = self.env['stock.package']

            while remaining_qty > 0:
                pallet_qty = min(remaining_qty, self.capacity_per_pallet)
                package_vals = {
                    'production_id': self.production_id.id,
                    'pallet_state': state,
                    'target_qty': pallet_qty,
                }
                if self.package_type_id:
                    package_vals['package_type_id'] = self.package_type_id.id

                package = self.env['stock.package'].create(package_vals)
                created_packages |= package

                remaining_qty -= pallet_qty

        # Try packing immediately from already-produced stock (supports partial MO).
        self.production_id._pack_missing_pallet_quantities(created_packages)

        _logger.info(
            'MO %s: Created/updated %d pallets for total qty %.2f via wizard.',
            self.production_id.name, len(created_packages), self.total_quantity,
        )

        self.production_id.message_post(
            body=_("Created/Updated <b>%d</b> pallets for a total quantity of <b>%s</b>") % (
                len(created_packages),
                self.total_quantity,
            ),
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )

        if len(created_packages) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'stock.package',
                'res_id': created_packages[0].id,
                'view_mode': 'form',
            }
        else:
            return self.production_id.action_view_pallets()
