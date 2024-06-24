# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import uuid

from odoo import api, fields, models


class ESBBus(models.Model):
    _name = 'esb.bus'
    _rec_name = 'channel'

    channel = fields.Char()
    ttype = fields.Char(string="Type")
    data = fields.Many2one(comodel_name='esb.data')
    uuid = fields.Char(default=uuid.uuid4())

    @api.model_create_multi
    def create(self, vals_list):
        res_list = super().create(vals_list)

        for res in res_list:
            # on va chercher les règles qui sont configurées sur le channel / ttype
            rules = self.env['esb.rule'].search([('channel', '=', res.channel), ('ttype', '=', res.ttype)])
            for rule in rules:
                res = rule.service.execute_with_delay(args=res.data)
                job = self.env['queue.job'].search([('uuid', '=', res._uuid)])
                self.env['esb.history'].create({'service': rule.service.id, 'bus': res.id, 'job': job.id})

        return res_list
