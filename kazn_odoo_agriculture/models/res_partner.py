from odoo import api, fields, models
class ResPartner(models.Model):
    _inherit = "res.partner"
    is_farmer = fields.Boolean(string='Is Farmer?',copy=True)
    is_location = fields.Boolean(string='Is Location?',copy=True)
    is_animal = fields.Boolean(string='Is Animal?',copy=True)
    crop_ids = fields.Many2many('farmer.location.crops',string='Crops',)
    def action_open_location_map(self):
        """
        Open a website route showing the partner on a Google Map.
        """
        location_action = {
           'type': 'ir.actions.act_url',
           'name': "Location",
           'target': 'new',
           'url': '/customers/%s' % (self.id)}
        return location_action