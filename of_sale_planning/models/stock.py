# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.one
    @api.depends('move_lines.date_expected', 'of_intervention_ids', 'of_intervention_ids.date', 'sale_id',
                 'sale_id.of_date_de_pose')
    def _compute_dates(self):
        res = super(StockPicking, self)._compute_dates()
        if self.env['ir.values'].get_default(
                'stock.config.settings', 'of_picking_min_date_compute_method') == 'planning':
            if self.of_intervention_ids:
                last_inter = self.of_intervention_ids.sorted('date')[-1]
                self.min_date = last_inter.date
            elif self.sale_id and self.sale_id.of_date_de_pose:
                self.min_date = self.sale_id.of_date_de_pose
        return res


class StockConfigSettings(models.TransientModel):
    _inherit = 'stock.config.settings'

    of_picking_min_date_compute_method = fields.Selection(
        selection=[('standard', u"Standard"),
                   ('planning', u"Valorisation basée sur la date des RDV d'intervention liés ou à défaut de la date "
                                u"de pose prévisionnelle de la commande associée, ou à défaut Standard Odoo")],
        string=u"(OF) Méthode de valorisation de la date prévue du BL", required=True, default='standard')

    @api.multi
    def set_of_picking_min_date_compute_method(self):
        return self.env['ir.values'].sudo().set_default(
            'stock.config.settings', 'of_picking_min_date_compute_method', self.of_picking_min_date_compute_method)
