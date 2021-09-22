# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OfInterventionSettings(models.TransientModel):
    _inherit = 'of.intervention.settings'

    of_contract = fields.Boolean(
        string="Utiliser les contrats",)

    @api.multi
    def set_of_contract_defaults(self):
        self = self.sudo()
        lecture = self.env.ref('of_contract_custom.group_of_contract_custom_lecture')
        modification = self.env.ref('of_contract_custom.group_of_contract_custom_modification')
        creation = self.env.ref('of_contract_custom.group_of_contract_custom_creation')
        if self.of_contract:
            users = self.env['res.users'].search([])
            users = users.filtered(lambda u: not u.has_group('of_contract_custom.group_of_contract_custom_lecture'))
            to_add = [(4, user.id) for user in users]
            if to_add:
                lecture.write({'users': to_add})
        else:
            lecture.write({'users': [(5,)]})
            modification.write({'users': [(5,)]})
            creation.write({'users': [(5,)]})
        return self.env['ir.values'].set_default(
            'of.intervention.settings', 'of_contract', self.of_contract)
