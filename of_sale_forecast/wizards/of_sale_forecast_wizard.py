# -*- coding: utf-8 -*-

from odoo import api, fields, models, registry
from odoo.exceptions import UserError

import threading


class OFSaleForecastWizard(models.TransientModel):
    _name = 'of.sale.forecast.wizard'
    _description = u"Assistant de prévision de vente"

    @api.model
    def _default_warehouse_id(self):
        company_user = self.env.user.company_id
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', company_user.id)], limit=1)
        if warehouse:
            return warehouse.id
        else:
            raise UserError(u"Vous devez définir un entrepôt pour la société : %s." % (company_user.name,))

    forecast_date = fields.Date(string=u"Date de prévision", required=True)
    brand_id = fields.Many2one(comodel_name='of.product.brand', string=u"Marque", required=True)
    categ_id = fields.Many2one(comodel_name='product.category', string=u"Catégorie")
    company_id = fields.Many2one(
        comodel_name='res.company', string=u"Société", required=True,
        default=lambda self: self.env['res.company']._company_default_get())
    warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse', string=u"Entrepôt", required=True, default=_default_warehouse_id)
    forecast_method = fields.Selection(
        selection=[('evol_n_1', u"Taux d'évolution N-1"),
                   ('evol_3_years', u"Taux d'évolution sur 3 ans"),
                   ('tend_n_1', u"Tendance N-1")],
        string=u"Méthode", required=True)
    forecast_method_value = fields.Float(string=u"Valeur")

    @api.multi
    def _generate_forecasts(self):
        self.ensure_one()

        product_domain = [('brand_id', '=', self.brand_id.id)]
        if self.categ_id:
            product_domain += [('categ_id', '=', self.categ_id.id)]
        products = self.env['product.product'].search(product_domain)

        for product in products:
            sale_forecast = self.env['of.sale.forecast'].create({
                'product_id': product.id,
                'forecast_date': self.forecast_date,
                'company_id': self.company_id.id,
                'warehouse_id': self.warehouse_id.id,
                'forecast_method': self.forecast_method,
                'forecast_method_value': self.forecast_method_value,
            })
            sale_forecast.action_compute_history()
            sale_forecast.action_compute_forecast_lines()
            sale_forecast.action_compute_forecast()

            self._cr.commit()

        return True

    @api.multi
    def _forecast_generation_all(self):
        with api.Environment.manage():
            # As this function is in a new thread, i need to open a new cursor, because the old one may be closed
            new_cr = registry(self._cr.dbname).cursor()
            self = self.with_env(self.env(cr=new_cr))

            self._generate_forecasts()

            # close the new cursor
            self._cr.close()
            return {}

    @api.multi
    def forecast_generation(self):
        threaded_calculation = threading.Thread(target=self._forecast_generation_all, args=())
        threaded_calculation.start()
        return {'type': 'ir.actions.act_window_close'}
