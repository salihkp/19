from odoo import api, fields, models
class CropsDieases(models.Model):
    """
    Technical model name and field names preserved to avoid migration.
    User-facing labels use correct spelling: 'Diseases', 'Cures'.
    """
    _name = 'crops.dieases'
    _rec_name = 'crops_dieases_cure_id'
    description = fields.Text(string='Description',required=True)
    crops_dieases_cure_id = fields.Many2one('crops.dieases.cure',string="Crops Dieases Cure",required=True)
    crops_dieases_cures_id = fields.Many2one('farmer.location.crops',string="Crops",required=True)
    @api.onchange('crops_dieases_cure_id')
    def _onchange_crops_dieases_cure_id(self):
        """Auto-fill description from the selected cure."""
        if self.crops_dieases_cure_id:
            self.description = self.crops_dieases_cure_id.description
class CropsDieasesCure(models.Model):
    _name = 'crops.dieases.cure'
    _rec_name = 'name'
    name = fields.Char(string='Name',required=True)
    description = fields.Text(string='Description',required=True)