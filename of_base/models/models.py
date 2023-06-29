# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from bs4 import BeautifulSoup as BSHTML

from odoo import api, models

OF_MODELS_TO_SANITIZE = [
    'account.invoice',
    'base.comment.template',
    'crm.lead',
    'document.document',
    'of.planning.intervention',
    'project.task',
    'sale.order',
]


class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def html_sanitize_img(self, record, html_text):
        soup = BSHTML(html_text)
        images = soup.find_all('img')
        attachment_obj = self.env['ir.attachment']
        # Find existing attachments
        attachment_nb = attachment_obj.search_count(
            [('res_model', '=', record._name), ('res_id', '=', record.id), ('of_internal', '=', True)])
        count = attachment_nb
        image_found = False
        for image in images:
            file_ext = ''
            img_src = ''
            mimetype = ''
            if image.has_attr('src') and image['src'].startswith('data:image/png;base64,'):
                file_ext = '.png'
                img_src = image['src'][22:]
                mimetype = 'image/png'
            elif image.has_attr('src') and image['src'].startswith('data:image/jpeg;base64,'):
                file_ext = '.jpg'
                img_src = image['src'][23:]
                mimetype = 'image/jpeg'
            if img_src:
                image_found = True
                count += 1
                img_name = '%s_%s' % (record.display_name.replace('/', '').replace(' ', '_'), count)
                attachment = attachment_obj.create(
                    {'name': img_name,
                     'datas_fname': img_name + file_ext,
                     'datas': img_src,
                     'mimetype': mimetype,
                     'res_model': record._name,
                     'res_id': record.id,
                     'of_internal': True,
                     })
                image['src'] = '/web/content/%s' % attachment.id
        if image_found:
            return str(soup)
        else:
            return False

    @api.model
    def create(self, vals):
        record = super(Base, self).create(vals)
        if self._name in OF_MODELS_TO_SANITIZE:
            new_vals = {}
            for name, val in vals.items():
                field = self._fields.get(name)
                if field and field.type == 'html' and field.store and val:
                    new_val = self.html_sanitize_img(record, val)
                    if new_val:
                        new_vals[name] = new_val
            if new_vals:
                record.write(new_vals)
        return record

    @api.multi
    def write(self, vals):
        if self._name in OF_MODELS_TO_SANITIZE:
            for name, val in vals.items():
                field = self._fields.get(name)
                if field and field.type == 'html' and field.store and val:
                    new_val = False
                    for record in self:
                        new_val = self.html_sanitize_img(record, val)
                        if new_val:
                            record.write({name: new_val})
                    if new_val:
                        del vals[name]
        res = super(Base, self).write(vals)
        return res
