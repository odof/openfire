# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.onchange('zip')
    def _onchange_zip(self):
        self.ensure_one()
        if self.zip and self.env['ir.values'].get_default('of.intervention.settings', 'automatic_areas'):
            self.of_secteur_com_id = self.env['of.secteur'].get_secteur_from_cp(self.zip).filtered(
                lambda sec: sec.type in ('com', 'tech_com'))
            self.of_secteur_tech_id = self.env['of.secteur'].get_secteur_from_cp(self.zip).filtered(
                lambda sec: sec.type in ('tech', 'tech_com'))
