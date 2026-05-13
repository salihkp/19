# -*- coding: utf-8 -*-
from odoo import api, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def action_recompute_risk(self):
        """Trigger risk recomputation for federation partners.

        Called from the federation form button or scheduled action.
        Only processes records with is_federation = True.
        """
        scorer = self.env['ministry.risk.scorer']
        for partner in self.filtered('is_federation'):
            scorer.score_federation(partner)
