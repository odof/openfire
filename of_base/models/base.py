# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from bs4 import BeautifulSoup as BSHTML

from odoo import api, models

OF_MODELS_TO_SANITIZE = ['account.move', 'crm.lead', 'project.task', 'sale.order', 'res.partner']


class Base(models.AbstractModel):
    _inherit = 'base'

    def _get_models_to_html_sanitize(self):
        return OF_MODELS_TO_SANITIZE

    @api.model
    def html_sanitize_img(self, record, html_text):
        soup = BSHTML(html_text, features="html.parser")
        images = soup.find_all('img')
        attachment_obj = self.env['ir.attachment']
        # Find existing attachments
        attachment_nb = attachment_obj.search_count(
            [('res_model', '=', record._name), ('res_id', '=', record.id), ('of_internal', '=', True)]
        )
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
                img_name = f"{record.display_name.replace('/', '').replace(' ', '_')}_{count}"
                attachment = attachment_obj.create(
                    {
                        'name': img_name,
                        'store_fname': img_name + file_ext,
                        'datas': img_src,
                        'mimetype': mimetype,
                        'res_model': record._name,
                        'res_id': record.id,
                        'of_internal': True,
                    }
                )
                image['src'] = f'/web/content/{attachment.id}'
        return str(soup) if image_found else False

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if self._name in self._get_models_to_html_sanitize():
            for record, vals in zip(records, vals_list):
                new_vals = {}
                for name, val in vals.items():
                    field = self._fields.get(name)
                    if field and field.type == 'html' and field.store and val:
                        if new_val := self.html_sanitize_img(record, val):
                            new_vals[name] = new_val
                if new_vals:
                    record.write(new_vals)
        return records

    def write(self, vals):
        if self._name in self._get_models_to_html_sanitize():
            tmp_vals = vals.copy()
            for name, val in tmp_vals.items():
                field = self._fields.get(name)
                if field and field.type == 'html' and field.store and val:
                    new_val = False
                    for record in self:
                        new_val = self.html_sanitize_img(record, val)
                        if new_val:
                            record.write({name: new_val})
                    if new_val:
                        del vals[name]
        return super().write(vals)
