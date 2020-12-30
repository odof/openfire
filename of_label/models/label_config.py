# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# 1:  imports of odoo
from odoo import models, fields, api


class LabelBrand(models.Model):
    _name = 'label.brand'
    _rec_name = 'brand_name'
    _order = 'sequence'

    brand_name = fields.Char('Name', size=64, index=True)
    label_config_ids = fields.One2many('label.config', 'label_main_id',
                                       'Label Config')

    active = fields.Boolean(string=u"Actif", default=True)
    sequence = fields.Integer(string=u"Séquence")

    @api.multi
    def toggle_active(self):
        """ Héritage pour activer / archiver les lignes en même temps que la marque """
        super(LabelBrand, self).toggle_active()
        for record in self:
            for line in record.label_config_ids:
                line.active = record.active

    @api.multi
    def get_default_label_config(self):
        self.ensure_one
        return self.label_config_ids[0]


class LabelConfig(models.Model):
    _name = 'label.config'
    _order = 'sequence'

    name = fields.Char("Name", size=64, required=True, index=True)
    height = fields.Float("Height (in mm)", required=True)
    width = fields.Float("Width (in mm)", required=True)
    top_margin = fields.Float("Top Margin (in mm)", default=0.0)
    bottom_margin = fields.Float("Bottom Margin  (in mm)", default=0.0)
    left_margin = fields.Float("Left Margin (in mm)", default=0.0)
    right_margin = fields.Float("Right Margin (in mm)", default=0.0)
    cell_spacing = fields.Float("Cell Spacing", default=1.0)
    label_main_id = fields.Many2one('label.brand', 'Label')
    landscape = fields.Boolean(string=u"Paysage")

    active = fields.Boolean(string=u"Actif", default=True)
    sequence = fields.Integer(string=u"Séquence")
