# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import api, models, fields


class OFUpdateRecRulesWizard(models.TransientModel):
    _inherit = 'of.update.rec.rules.wizard'

    partner_ids = fields.Many2many(
        comodel_name='res.partner', relation='of_partner_intervention_rec_rules_rel', column1='intervention_id',
        column2='partner_id', string="Other participants")

    @api.multi
    def get_write_vals(self, with_rec=True, all=False):
        write_vals = super(OFUpdateRecRulesWizard, self).get_write_vals(with_rec=with_rec, all=all)
        write_vals['partner_ids'] = [(6, 0, self.partner_ids.ids)]
        return write_vals
