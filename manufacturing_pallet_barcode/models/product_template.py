from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    needs_sticker = fields.Boolean(
        string='Needs Sticker',
        default=False,
        help='Check if this product requires applying a sticker to its pallets during manufacturing',
    )

    sticker_product_id = fields.Many2one(
        'product.product',
        string='Sticker Product',
        domain="[('type', '=', 'consu')]",
        help='The consumable product used as a sticker when applying stickers to pallets',
    )

    @api.constrains('sticker_product_id')
    def _check_sticker_product(self):
        for tmpl in self:
            if tmpl.sticker_product_id and tmpl.sticker_product_id.product_tmpl_id == tmpl:
                raise ValidationError(_('A product cannot be its own sticker product.'))
