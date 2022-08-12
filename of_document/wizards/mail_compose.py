# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class EmailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    of_dms_file_ids = fields.Many2many(comodel_name='muk_dms.file', string=u"Documents GED")
    of_dms_directory_ids = fields.Many2many(
        comodel_name='muk_dms.directory', string=u"Dossiers GED", compute='_compute_of_dms_directory_ids')

    @api.multi
    @api.depends('partner_ids')
    def _compute_of_dms_directory_ids(self):
        dms_directory_obj = self.env['muk_dms.directory']
        for mail_compose in self:
            mail_compose.of_dms_directory_ids = dms_directory_obj.search(
                [('of_partner_id', 'in', mail_compose.partner_ids.ids)])

    @api.multi
    def get_mail_values(self, res_ids):
        res = super(EmailComposeMessage, self).get_mail_values(res_ids)
        if self.of_dms_file_ids:
            for res_id, res_dict in res.items():
                res_dict['attachment_ids'] += self.of_dms_file_ids.mapped('of_attachment_id').ids

        return res
