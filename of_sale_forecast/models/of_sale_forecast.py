# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round

from dateutil.relativedelta import relativedelta

MONTHS = (None, u"Janvier", u"Février", u"Mars", u"Avril", u"Mai", u"Juin", u"Juillet", u"Août", u"Septembre",
          u"Octobre", u"Novembre", u"Décembre")


class OFSaleForecast(models.Model):
    _name = 'of.sale.forecast'
    _inherit = 'mail.thread'
    _description = u"Prévision de vente"

    @api.model
    def _default_warehouse_id(self):
        company_user = self.env.user.company_id
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', company_user.id)], limit=1)
        if warehouse:
            return warehouse.id
        else:
            raise UserError(u"Vous devez définir un entrepôt pour la société : %s." % (company_user.name,))

    state = fields.Selection(
        selection=[('draft', u"Brouillon"),
                   ('confirm', u"Validé"),
                   ('cancel', u"Annulé")],
        string=u"État", required=True, default='draft', track_visibility='onchange')
    product_id = fields.Many2one(
        comodel_name='product.product', string=u"Article", readonly=True, required=True,
        states={'draft': [('readonly', False)]})
    product_categ_id = fields.Many2one(
        related='product_id.categ_id', string=u"Catégorie d'article", readonly=True, store=True)
    product_brand_id = fields.Many2one(
        related='product_id.brand_id', string=u"Marque de l'article", readonly=True, store=True)
    forecast_date = fields.Date(
        string=u"Date de prévision", readonly=True, required=True, states={'draft': [('readonly', False)]})
    confirmation_date = fields.Date(string=u"Date de validation")
    company_id = fields.Many2one(
        comodel_name='res.company', string=u"Société", readonly=True, index=True, required=True,
        states={'draft': [('readonly', False)]}, default=lambda self: self.env['res.company']._company_default_get())
    warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse', string=u"Entrepôt", readonly=True, required=True,
        states={'draft': [('readonly', False)]}, default=lambda s: s._default_warehouse_id())
    note = fields.Text(string=u"Notes")
    overview_line_ids = fields.One2many(
        comodel_name='of.sale.forecast.overview.line', inverse_name='sale_forecast_id', string=u"Lignes de synthèse")
    forecast_method = fields.Selection(
        selection=[('manual', u"Saisie manuelle"),
                   ('evol_n_1', u"Taux d'évolution N-1"),
                   ('evol_3_years', u"Taux d'évolution sur 3 ans"),
                   ('tend_n_1', u"Tendance N-1")],
        string=u"Méthode de prévision", readonly=True, states={'draft': [('readonly', False)]})
    forecast_method_value = fields.Float(
        string=u"Valeur de la méthode de prévision", readonly=True, states={'draft': [('readonly', False)]})
    forecast_line_ids = fields.One2many(
        comodel_name='of.sale.forecast.forecast.line', inverse_name='sale_forecast_id', string=u"Lignes de prévision")

    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            name = "%s - %s" % \
                   (rec.product_id.default_code, fields.Date.from_string(rec.forecast_date).strftime('%d/%m/%Y'))
            res.append((rec.id, name))
        return res

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id:
            warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)], limit=1)
            if warehouse:
                self.warehouse_id = warehouse
            else:
                raise UserError(u"Vous devez définir un entrepôt pour la société : %s." % (self.company_id.name,))
        else:
            self.warehouse_id = False

    @api.model
    def create(self, vals):
        # Modification de la date de prévision au premier jour du mois
        vals['forecast_date'] = fields.Date.from_string(vals.get('forecast_date')).strftime('%Y-%m-01')
        return super(OFSaleForecast, self).create(vals)

    @api.multi
    def write(self, vals):
        # Modification de la date de prévision au premier jour du mois
        if vals.get('forecast_date', False):
            vals['forecast_date'] = fields.Date.from_string(vals.get('forecast_date')).strftime('%Y-%m-01')
        return super(OFSaleForecast, self).write(vals)

    @api.multi
    def action_confirm(self):
        self.ensure_one()
        self.state = 'confirm'
        self.confirmation_date = fields.Date.today()
        return True

    @api.multi
    def action_cancel(self):
        self.ensure_one()
        self.state = 'cancel'
        return True

    @api.multi
    def action_set_to_draft(self):
        self.ensure_one()
        self.state = 'draft'
        return True

    @api.multi
    def action_compute_history(self):
        self.ensure_one()

        self.overview_line_ids.unlink()

        overview_lines = []
        forecast_year = fields.Date.from_string(self.forecast_date).year
        for m in range(1, 13):
            data = []

            for y in range(forecast_year - 4, forecast_year + 1):
                start_date = fields.Date.from_string("%d-%02d-01" % (y, m))
                if y == forecast_year and fields.Date.to_string(start_date) >= fields.Date.today():
                    continue
                end_date = start_date + relativedelta(months=1)

                # Quantité vendue
                qty = sum(self.env['sale.order.line'].search(
                    [('product_id', '=', self.product_id.id),
                     ('order_id.state', 'in', ('sale', 'done')),
                     ('order_id.confirmation_date', '>=', fields.Date.to_string(start_date)),
                     ('order_id.confirmation_date', '<', fields.Date.to_string(end_date))]
                ).mapped('product_uom_qty'))
                data.append(qty)

            overview_line_vals = {
                'sequence': m,
                'name': MONTHS[m],
                'n_4_qty': data[0],
                'n_3_qty': data[1],
                'n_3_evol_n_1': data[1] - data[0],
                'n_2_qty': data[2],
                'n_2_evol_n_1': data[2] - data[1],
                'n_1_qty': data[3],
                'n_1_evol_n_1': data[3] - data[2],
                'forecast_qty': len(data) == 5 and data[4] or 0.0,
                'forecast_evol_n_1': len(data) == 5 and data[4] - data[3] or 0.0,
            }

            overview_lines.append((0, 0, overview_line_vals))

        # Poids
        n_3_total = sum(overview_lines[m-1][2]['n_3_qty'] for m in range(1, 13))
        n_2_total = sum(overview_lines[m-1][2]['n_2_qty'] for m in range(1, 13))
        n_1_total = sum(overview_lines[m-1][2]['n_1_qty'] for m in range(1, 13))
        for m in range(1, 13):
            if n_3_total:
                overview_lines[m - 1][2]['n_3_weight'] = 100.0 * overview_lines[m-1][2]['n_3_qty'] / n_3_total
            else:
                overview_lines[m - 1][2]['n_3_weight'] = 0.0
            if n_2_total:
                overview_lines[m - 1][2]['n_2_weight'] = 100.0 * overview_lines[m-1][2]['n_2_qty'] / n_2_total
            else:
                overview_lines[m - 1][2]['n_2_weight'] = 0.0
            if n_1_total:
                overview_lines[m - 1][2]['n_1_weight'] = 100.0 * overview_lines[m-1][2]['n_1_qty'] / n_1_total
            else:
                overview_lines[m - 1][2]['n_1_weight'] = 0.0

        # Évolution P-1
        for m in range(1, 13):
            if m == 1:
                overview_lines[0][2]['n_3_evol_p_1'] = \
                    overview_lines[0][2]['n_3_qty'] - overview_lines[11][2]['n_4_qty']
                overview_lines[0][2]['n_2_evol_p_1'] = \
                    overview_lines[0][2]['n_2_qty'] - overview_lines[11][2]['n_3_qty']
                overview_lines[0][2]['n_1_evol_p_1'] = \
                    overview_lines[0][2]['n_1_qty'] - overview_lines[11][2]['n_2_qty']
            else:
                overview_lines[m - 1][2]['n_3_evol_p_1'] = \
                    overview_lines[m - 1][2]['n_3_qty'] - overview_lines[m - 2][2]['n_3_qty']
                overview_lines[m - 1][2]['n_2_evol_p_1'] = \
                    overview_lines[m - 1][2]['n_2_qty'] - overview_lines[m - 2][2]['n_2_qty']
                overview_lines[m - 1][2]['n_1_evol_p_1'] = \
                    overview_lines[m - 1][2]['n_1_qty'] - overview_lines[m - 2][2]['n_1_qty']

        self.overview_line_ids = overview_lines

        return True

    @api.multi
    def action_compute_forecast(self):
        self.ensure_one()

        for m in range(1, 13):
            forecast_line = self.forecast_line_ids.filtered(lambda l: l.sequence == m)
            if forecast_line:
                overview_line = self.overview_line_ids.filtered(lambda l: l.sequence == m)
                if overview_line:
                    overview_line.write({'forecast_qty': forecast_line.quantity,
                                         'forecast_evol_n_1': forecast_line.quantity - overview_line.n_1_qty,
                                         'forecast': True})

        # Poids
        forecast_total = sum(self.overview_line_ids.mapped('forecast_qty'))
        if forecast_total:
            for m in range(1, 13):
                overview_line = self.overview_line_ids.filtered(lambda l: l.sequence == m)
                if overview_line:
                    overview_line.forecast_weight = 100.0 * overview_line.forecast_qty / forecast_total

        # Évolution P-1
        for m in range(1, 13):
            overview_line = self.overview_line_ids.filtered(lambda l: l.sequence == m)
            if overview_line:
                if m == 1:
                    qty_p_1 = self.overview_line_ids.filtered(lambda l: l.sequence == 12).n_1_qty
                else:
                    qty_p_1 = self.overview_line_ids.filtered(lambda l: l.sequence == m - 1).forecast_qty
                overview_line.forecast_evol_p_1 = overview_line.forecast_qty - qty_p_1

        return True

    @api.multi
    def action_compute_forecast_lines(self):
        self.ensure_one()

        if not self.forecast_method:
            raise UserError(u"Vous devez définir une méthode de prévision.")

        self.forecast_line_ids.filtered(lambda l: not l.locked).unlink()

        forecast_lines = []
        forecast_year = fields.Date.from_string(self.forecast_date).year

        for m in range(1, 13):
            start_date = fields.Date.from_string("%d-%02d-01" % (forecast_year, m))
            if fields.Date.to_string(start_date) <= fields.Date.today() or \
                    self.forecast_line_ids.filtered(lambda l: l.sequence == m):
                continue
            end_date = start_date + relativedelta(months=1, days=-1)

            # Calcul des quantités prévisionnelles
            quantity = 0.0
            overview_line = self.overview_line_ids.filtered(lambda l: l.sequence == m)
            if overview_line:
                if self.forecast_method == 'evol_n_1':
                    quantity = overview_line.n_1_qty + (overview_line.n_1_qty * self.forecast_method_value / 100.0)
                elif self.forecast_method == 'evol_3_years':
                    n_2_evol = overview_line.n_2_evol_n_1
                    n_1_evol = overview_line.n_1_evol_n_1
                    forecast_evol = (n_2_evol + n_1_evol) / 2.0
                    quantity = overview_line.n_1_qty + forecast_evol
                elif self.forecast_method == 'tend_n_1':
                    quantity = overview_line.n_1_qty + overview_line.n_1_evol_n_1

            rounding = self.product_id.uom_id.rounding
            quantity = max(float_round(quantity, precision_rounding=rounding), 0.0)

            forecast_line_vals = {
                'sequence': m,
                'name': MONTHS[m],
                'start_date': start_date,
                'end_date': end_date,
                'quantity': quantity,
            }

            forecast_lines.append((0, 0, forecast_line_vals))

        self.forecast_line_ids = forecast_lines

        return True


class OFSaleForecastOverviewLine(models.Model):
    _name = 'of.sale.forecast.overview.line'
    _description = u"Ligne de synthèse de prévision de vente"
    _order = 'sequence'

    sale_forecast_id = fields.Many2one(
        comodel_name='of.sale.forecast', string=u"Prévision de vente", required=True, index=True, ondelete='cascade')
    name = fields.Char(string=u"Période", required=True)
    sequence = fields.Integer(string=u"Séquence")
    forecast = fields.Boolean(string=u"Prévision")
    n_3_qty = fields.Float(string=u"N - 3 // Qté")
    n_3_weight = fields.Float(string=u"N - 3 // Poids")
    n_3_evol_n_1 = fields.Float(string=u"N - 3 // Évol N-1")
    n_3_evol_p_1 = fields.Float(string=u"N - 3 // Évol P-1")
    n_2_qty = fields.Float(string=u"N - 2 // Qté")
    n_2_weight = fields.Float(string=u"N - 2 // Poids")
    n_2_evol_n_1 = fields.Float(string=u"N - 2 // Évol N-1")
    n_2_evol_p_1 = fields.Float(string=u"N - 2 // Évol P-1")
    n_1_qty = fields.Float(string=u"N - 1 // Qté")
    n_1_weight = fields.Float(string=u"N - 1 // Poids")
    n_1_evol_n_1 = fields.Float(string=u"N - 1 // Évol N-1")
    n_1_evol_p_1 = fields.Float(string=u"N - 1 // Évol P-1")
    forecast_qty = fields.Float(string=u"Prévision // Qté")
    forecast_weight = fields.Float(string=u"Prévision // Poids")
    forecast_evol_n_1 = fields.Float(string=u"Prévision // Évol N-1")
    forecast_evol_p_1 = fields.Float(string=u"Prévision // Évol P-1")


class OFSaleForecastForecastLine(models.Model):
    _name = 'of.sale.forecast.forecast.line'
    _description = u"Ligne de prévision de vente"
    _order = 'sequence'

    sale_forecast_id = fields.Many2one(
        comodel_name='of.sale.forecast', string=u"Prévision de vente", required=True, index=True, ondelete='cascade')
    name = fields.Char(string=u"Période", required=True)
    sequence = fields.Integer(string=u"Séquence")
    start_date = fields.Date(string=u"Date de début", required=True)
    end_date = fields.Date(string=u"Date de fin", required=True)
    quantity = fields.Float(string=u"Quantité")
    locked = fields.Boolean(string=u"Verrouillé")
    note = fields.Char(string=u"Notes")
