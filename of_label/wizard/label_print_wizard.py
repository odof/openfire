# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# 1: imports of python lib
import math

# 2:  imports of openerp
from odoo import fields, models, api
from odoo.tools import misc


class LabelPrintWizard(models.TransientModel):
    _name = 'label.print.wizard'

    @api.model
    def default_get(self, fields):
        result = super(LabelPrintWizard, self).default_get(fields)
        if self._context.get('label_print'):
            label_print_obj = self.env['label.print']
            label_print_data = label_print_obj.browse(
                self._context.get('label_print'))
            result['brand_id'] = label_print_data.label_brand_id and label_print_data.label_brand_id.id or False
            result['config_id'] = label_print_data.label_config_id and label_print_data.label_config_id.id or False
            image = label_print_data.field_ids.filtered(lambda c: c.type == 'image')
            if image:
                image = image[0]
                result['is_image'] = True
                result['image_width'] = image.width
                result['image_height'] = image.height
            barcode = label_print_data.field_ids.filtered(lambda c: c.type == 'barcode')
            if barcode:
                barcode = barcode[0]
                result['is_barcode'] = True
                result['barcode_width'] = barcode.width
                result['barcode_height'] = barcode.height
            if label_print_data.line_model_id and self._context.get('active_id'):
                # récupérer l'enregistrement qui contient les lignes pour les ajouter au wizard d'impression
                record = self.env[label_print_data.model_id.model].browse(self._context.get('active_id'))
                result['line_ids'] = [(0, 0, {'src_line_id_int': line.id,
                                              'name': line.name,
                                              'selected': True})
                                      for line in getattr(record, label_print_data.line_field_name)]
                result['use_line'] = True
                result['line_model'] = label_print_data.line_model_id.model
        return result

    config_id = fields.Many2one('label.config', 'Label Size', required=True)
    number_of_copy = fields.Integer('Number Of Copy', required=True, default=1)
    image_width = fields.Float('Width', default=50)
    image_height = fields.Float('Height', default=50)
    barcode_width = fields.Float('Width', default=50)
    barcode_height = fields.Float('Height', default=50)
    is_barcode = fields.Boolean('Is Barcode?')
    is_image = fields.Boolean('Is Image?')
    brand_id = fields.Many2one('label.brand', 'Brand Name', required=True)

    use_line = fields.Boolean(string=u"Utiliser les lignes")
    line_model = fields.Char(string=u"Modèle des lignes")
    line_ids = fields.One2many(
        comodel_name='of.label.print.wizard.line', inverse_name='wizard_id', string=u"Lignes à imprimer")
    line_selected_ids = fields.One2many(
        comodel_name='of.label.print.wizard.line', inverse_name='wizard_id', string=u"Lignes à imprimer",
        compute="_compute_line_selected_ids")

    @api.multi
    @api.depends('line_ids', 'line_ids.selected')
    def _compute_line_selected_ids(self):
        for wizard in self:
            wizard.line_selected_ids = wizard.line_ids.filtered(lambda l: l.selected)

    @api.multi
    def print_report(self):
        if self._context is None:
            self._context = {}
        label_print_id = self._context.get('label_print')
        if not label_print_id or not self._context.get('active_ids'):
            return False
        records = self.line_ids or self.browse(self.ids)
        if not records:
            return False
        label_print = self.env['label.print'].browse(self._context.get('label_print'))
        mode = label_print.mode
        record = records[0]
        if self.use_line:
            total_record = len(self.line_ids)
        else:
            total_record = len(self._context.get('active_ids', []))
        if self.use_line:
            wizard = record.wizard_id
            model = self.line_model
            ids = self.line_selected_ids.mapped('src_line_id_int')
        else:
            wizard = record
            model = self._context.get('active_model')
            ids = self._context.get('active_ids', [])
        landscape = wizard.config_id.landscape
        if landscape:
            page_width = 297.0
            page_height = 210.0
        else:
            page_width = 210.0
            page_height = 297.0
        column = page_width / float(wizard.config_id.width or 1)
        total_row = math.ceil(float(total_record) / (column or 1))
        no_row_per_page = int(page_height / wizard.config_id.height)
        height = int(page_height) / (no_row_per_page or 1)
        ratio = 4.555

        datas = {
            'rows': int(total_row),
            'columns': int(column) == 0 and 1 or int(column),
            'model': model,
            'height': str(int(height * ratio)) + "px",
            #'height': str(height * ratio) + "mm",
            'height_internal': str(int(height * ratio - 2)) + "px",
            #'height': str(int(height * 100.0 / 297)) + "%",
            'no_row_per_page': no_row_per_page,
            #'width': str(int(wizard.config_id.width * 100.0 / 210)) + "%",
            #'width': str(wizard.config_id.width * ratio) + "mm",
            'width': str(int(wizard.config_id.width * ratio)) + "px",
            'width_internal': str(int(wizard.config_id.width * ratio - 2)) + "px",
            'image_width': str(wizard.image_width),
            'image_height': str(wizard.image_height),
            'barcode_width': wizard.barcode_width,
            'barcode_height': wizard.barcode_height,
            'font_size': 10,
            'number_of_copy': wizard.number_of_copy,
            'top_margin': str(wizard.config_id.top_margin) + "mm",
            'bottom_margin': str(wizard.config_id.bottom_margin) + "mm",
            'left_margin': str(wizard.config_id.left_margin) + "mm",
            'right_margin': str(wizard.config_id.right_margin) + "mm",
            'cell_spacing': str(wizard.config_id.cell_spacing) + "px",
            'landscape': landscape,
            'ids': ids,
            'mode': mode,
            'template_css': label_print.template_css_id.xml_id or '',
        }
        if mode == 'template':
            datas['template_name'] = label_print.template_id.xml_id

        cr, uid, context = self.env.args
        context = dict(context)
        context.update({"label_print_id": label_print_id,
                        'datas': datas})
        self.env.args = cr, uid, misc.frozendict(context)

        if self.use_line:
            ids = self.line_selected_ids and self.line_selected_ids.ids or []
            if not ids:
                raise Warning(u"Vous devez sélectionner au moins une ligne pour imprimer des étiquettes")
        else:
            ids = self.ids
        data = {
            'ids': ids,
            'model': 'label.config',
            'form': datas,
            'landscape': landscape,
        }
        report_name = datas['landscape'] and 'of_label.report_label_landscape' or 'of_label.report_label'
        action = self.env['report'].get_action(self, report_name, data=data)
        return action


class OFLabelPrintWizardLine(models.TransientModel):
    _name = 'of.label.print.wizard.line'
    _description = u"Ligne d'impression d'étiquettes'"

    wizard_id = fields.Many2one(comodel_name='label.print.wizard', string=u"wizard")
    name = fields.Char(string=u"Ligne", readonly=True)
    src_line_id_int = fields.Integer(string=u"ID de ligne", readonly=True, help=u"de l'objet source")
    selected = fields.Boolean(string=u"Sélectionné")
