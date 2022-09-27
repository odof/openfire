# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

# 1: imports of python lib
from dateutil.relativedelta import relativedelta
# 2: imports of odoo
from odoo import models, fields, api
from odoo.tools.safe_eval import safe_eval
# 3: imports from odoo modules
# 4: local imports
# 5: Import of unknown third party lib


class OFContract(models.Model):
    _inherit = 'of.contract'

    @api.model
    def get_ctype_selection(self):
        ctype_selection = super(OFContract, self).get_ctype_selection()
        ctype_selection.append(('subscription', "d'abonnement"))
        return ctype_selection

    auto_invoicing = fields.Boolean(string="Facturation automatique")
    address_id = fields.Many2one(required=False)


class OFContractLine(models.Model):
    _inherit = 'of.contract.line'

    order_line_id = fields.Many2one(comodel_name='sale.order.line', string="Ligne de commande")


class OFContractProduct(models.Model):
    _inherit = 'of.contract.product'

    @api.depends('quantity', 'line_id', 'line_id.nbr_interv', 'line_id.next_date', 'line_id.state', 'qty_invoiced',
                 'line_id.current_period_id',
                 'line_id.frequency_type',
                 'line_id.recurring_invoicing_payment_id.code',
                 'line_id.revision',
                 'line_id.contract_id.period',
                 'invoice_line_ids',
                 'invoice_line_ids.quantity', 'invoice_line_ids.invoice_id',
                 'invoice_line_ids.invoice_id.state',)
    def _compute_quantities(self):
        """ Calcul de la qté à facturer """
        for product_line in self:
            line = product_line.line_id
            if line.ctype != 'subscription':
                super(OFContractProduct, product_line)._compute_quantities()
            else:
                qty_to_invoice = product_line.quantity
                product_line.qty_per_period = qty_to_invoice  # a corriger
                multiplier = 1
                if line.prorata:
                    if not line.invoice_line_ids.filtered(lambda il: il.invoice_id.state != 'cancel'):
                        start = fields.Date.from_string(line.date_start)
                        end = fields.Date.from_string(line.next_date or line.first_invoicing)
                        start_next_month = start + relativedelta(months=1, day=1)
                        start_beg_month = start + relativedelta(day=1)
                        diviseur = ((start_next_month - start_beg_month) + (end - start_next_month)).days
                        dividende = ((start_next_month - start) + (end - start_next_month)).days
                        # un des chiffres doit être cast en float autrement on trouve un arrondi
                        multiplier = float(dividende) / diviseur
                        if line.recurring_invoicing_payment_id.code == 'pre-paid':
                            # pre-paid signifie qu'on paie pour la période a venir donc qty = prorata + 1
                            multiplier += 1.0
                    elif line.date_end and line.next_date >= line.date_end:
                        start = fields.Date.from_string(line.next_date)
                        frequency = line.contract_id.frequency
                        amount = line.contract_id.frequency_amount
                        if frequency == 'trimester':
                            amount *= 3
                            frequency == 'month'
                        elif frequency == 'semester':
                            amount *= 15
                            frequency == 'week'
                        last_date = safe_eval('base_date + relativedelta(%s=amount)' % frequency,
                                              {'base_date': start,
                                               'relativedelta': relativedelta,
                                               'amount': amount}
                                              )
                        if line.recurring_invoicing_payment_id.code == 'pre-paid':
                            last_date += relativedelta(day=1)
                        elif line.recurring_invoicing_payment_id.code == 'post-paid':
                            last_date += relativedelta(months=1, day=1, days=-1)
                        end = fields.Date.from_string(line.date_end)
                        diviseur = last_date - start
                        dividende = end - start
                        # un des chiffres doit être cast en float autrement on trouve un arrondi
                        multiplier = float(dividende) / diviseur
                product_line.qty_to_invoice = qty_to_invoice * multiplier
