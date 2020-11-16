# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.addons.muk_dms.models import dms_base


class DatabaseDataModel(models.Model):
    _inherit = 'muk_dms.data_database'

    of_website_published = fields.Boolean(string=u"Publié sur le site internet")


class File(dms_base.DMSModel):
    _inherit = 'muk_dms.file'

    of_website_published = fields.Boolean(string=u"Publié sur le site internet")
    of_website_url = fields.Char(compute='_compute_of_website_url', string=u"Lien pour le site internet")

    @api.multi
    def website_publish_button(self):
        self.ensure_one()
        if self.of_file_type == 'normal':
            self = self.sudo()
            self.reference.of_website_published = not self.reference.of_website_published
            # Set datas_fname
            attachment = self.env['ir.attachment'].search(
                [('res_model', '=', self.reference._name), ('res_id', '=', self.reference.id),
                 ('res_field', '=', 'data'), ('datas_fname', '=', False)], limit=1)
            if attachment:
                attachment.datas_fname = self.name
        return self.write({'of_website_published': not self.of_website_published})

    @api.multi
    def _compute_of_website_url(self):
        for dms_file in self:
            if dms_file.of_file_type == 'normal':
                attachment = self.env['ir.attachment'].search(
                    [('res_model', '=', dms_file.reference._name), ('res_id', '=', dms_file.reference.id),
                     ('res_field', '=', 'data')], limit=1)
                dms_file.of_website_url = "/web/content/%s/?download=true" % attachment.id
            elif dms_file.of_file_type == 'related':
                dms_file.of_website_url = "/web/content/%s/?download=true" % dms_file.of_attachment_id.id
