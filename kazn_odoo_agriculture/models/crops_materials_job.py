# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CropsMaterialsJob(models.Model):
    """
    Planning line for Materials/Labour/Overheads used by a Crop.
    """
    _name = 'crops.materials.job'
    _description = 'Crop Materials Job'
    _rec_name = 'internal_type'

    internal_type = fields.Selection(
        [('material', 'Material'), ('labour', 'Labour'), ('overhead', 'Overhead')],
        string="Type", required=True,
        help="Category of this planning line: material input, labour cost, or overhead.")
    crop_id = fields.Many2one('farmer.location.crops', string="Crops", required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    quantity = fields.Float(string='Quantity', required=True)
    internal_note = fields.Text(string='Description')
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company,
        help="Company this planning line belongs to.")

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Default UoM and note from the selected product."""
        if self.product_id:
            self.uom_id = self.product_id.uom_id.id
            self.internal_note = self.product_id.name
