# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import timedelta
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


class OFOutlayAnalysis(models.Model):
    _name = 'of.outlay.analysis'
    _description = u"Analyse de débours"
    _order = 'state desc, name'

    name = fields.Char(string=u"Libellé")
    analytic_account_ids = fields.Many2many(
        comodel_name='account.analytic.account',
        string=u"Comptes analytiques",
        required=True
    )
    # En réalité, tous ces champs devraient être calculés grâce à leur compte analytique...
    # analytic_section_ids = fields.Many2many(
    #     comodel_name='of.account.analytic.section',
    #     string=u"Sections analytiques"
    # )
    # user_id = fields.Many2one(comodel_name='res.users', string=u"Responsable")
    # company_id = fields.Many2one(comodel_name='res.company', string=u"Société")
    # init_sale_ids = fields.Many2many(comodel_name='sale.order', string=u"CC Initiales")
    # compl_sale_ids = fields.Many2many(comodel_name='sale.order', string=u"CC complémentaires")
    # purchase_ids = fields.Many2many(comodel_name='purchase.order', string=u"Commandes fournisseur")
    # out_invoice_ids = fields.Many2many(
    #     comodel_name='account.invoice', string=u"Factures client",
    #     domain="[('type', 'in', ('out_invoice', 'out_refund'))]"
    # )
    # in_invoice_ids = fields.Many2many(
    #     comodel_name='account.invoice', string=u"Factures client",
    #     domain="[('type', 'in', ('in_invoice', 'in_refund'))]"
    # )
    # out_journal_ids = fields.Many2many(comodel_name='account.journal', string=u"Journaux")
    # in_journal_ids = fields.Many2many(comodel_name='account.journal', string=u"Journaux")
    # stock_move_ids = fields.Many2many(
    #     comodel_name='stock.move', string=u"Bons de livraison",
    #     domain="[('picking_type_id.code', '=', 'outgoing')]"
    # )
    # task_ids = fields.Many2many(comodel_name='project.task', string=u"Tâches")
    # user_ids = fields.Many2many(comodel_name='res.users', string=u"Utilisateurs")
    # intervention_ids = fields.Many2many(comodel_name='of.planning.intervention', string=u"RDVs")
    sale_order_ids = fields.Many2many(
        comodel_name='sale.order', string=u"Bons de commande", compute='_compute_sale_order_ids')
    sales_total = fields.Float(string=u"CA", compute='_compute_sale_order_ids')
    value_ids = fields.One2many(comodel_name='of.outlay.analysis.value', inverse_name='analysis_id', string=u"Valeurs")
    expected_expenses = fields.Float(string=u"Dépenses estimées")
    state = fields.Selection(
        selection=[('open', u"Ouvert"), ('closed', u"Fermé")],
        sttring=u"État", default='open', required=True
    )

    @api.onchange('init_sale_ids')
    def _onchange_init_sale_ids(self):
        if self.init_sale_ids & self.compl_sale_ids:
            self.compl_sale_ids -= self.init_sale_ids

    @api.onchange('compl_sale_ids')
    def _onchange_compl_sale_ids(self):
        if self.init_sale_ids & self.compl_sale_ids:
            self.init_sale_ids -= self.compl_sale_ids

    @api.depends('analytic_account_ids')
    def _compute_sale_order_ids(self):
        sale_obj = self.env['sale.order']
        for analysis in self:
            orders = sale_obj.search(
                [('project_id', 'in', self.analytic_account_ids.ids), ('state', 'in', ('sale', 'done'))]
            )
            analysis.sale_order_ids = orders
            analysis.sales_total = sum(orders.mapped('amount_untaxed'))

    @api.multi
    def action_open(self):
        self.write({'state': 'open'})

    @api.multi
    def action_close(self):
        self.write({'state': 'close'})

    @api.multi
    def action_recompute_values(self):
        self.ensure_one()
        self = self.sudo()
        value_obj = self.env['of.outlay.analysis.value']
        if not self.sale_order_ids:
            raise UserError(u"Vous devez renseigner au moins 1 bon de commande client")
        sale_order_lines = self.sale_order_ids.mapped('order_line').sorted(
            key=lambda l: (l.date_order, l.order_id.project_id.id, l.of_analytic_section_id.id)
        )
        if not sale_order_lines:
            raise UserError(u"Vous devez renseigner au moins 1 bon de commande client ayant des lignes de commande")
        purchase_order_lines = self.env['purchase.order.line'].search(
            [('account_analytic_id', 'in', self.analytic_account_ids.ids), ('state', 'in', ('purchase', 'done'))],
            order='date_order, account_analytic_id, of_analytic_section_id'
        )

        # invoice_lines = self.env['account.invoice.line'].search(
        #     [('project_id', 'in', self.analytic_account_ids.ids)],
        #     order='date'
        # )
        # sale_invoice_lines = invoice_lines.filtered(
        #     lambda i: i.invoice_id.state in ('open', 'paid') and i.invoice_id.type in ('out_invoice', 'out_refund')
        # )
        # purchase_invoice_lines = invoice_lines.filtered(
        #     lambda i: i.invoice_id.state in ('open', 'paid') and i.invoice_id.type in ('in_invoice', 'in_refund')
        # )

        move_lines = self.env['account.move.line'].search(
            [('analytic_account_id', 'in', self.analytic_account_ids.ids)],
            order='date, analytic_account_id, of_analytic_section_id'
        )
        out_move_lines = move_lines.filtered(lambda l: l.account_id.code.startswith('6'))
        in_move_lines = move_lines.filtered(lambda l: l.account_id.code.startswith('7'))

        self.value_ids.unlink()
        date_min = fields.Date.from_string(min(filter(None, (
            sale_order_lines[0].date_order,
            purchase_order_lines[:1].date_order,
            move_lines[:1].date,
        ))))
        date_min -= timedelta(days=date_min.day - 1)
        date_max = fields.Date.from_string(max(
            sale_order_lines[-1].date_order,
            purchase_order_lines[-1:].date_order,
            move_lines[-1:].date,
            fields.Date.today())
        )
        date_max += relativedelta(months=1, day=1)

        # type out_expected : valeur saisie en dur
        date = date_min
        while date < date_max:
            value_obj.create({
                'analysis_id': self.id,
                'date': fields.Date.to_string(date),
                'type': 'out_expected',
                'analytic_account_id': False,
                'analytic_section_id': False,
                'amount': self.expected_expenses,
            })
            date += relativedelta(months=1)

        for value_type, records, amount_field, sign, analytic_account_field, date_field, in (
            ('in_expected', sale_order_lines, 'price_subtotal', 1, 'order_id.project_id', 'date_order'),
            ('in_invoiced', in_move_lines, 'balance', -1, 'analytic_account_id', 'date'),
            ('out_ordered', purchase_order_lines, 'price_subtotal', 1, 'account_analytic_id', 'date_order'),
            ('out_invoiced', out_move_lines, 'balance', 1, 'analytic_account_id', 'date'),
        ):
            if not records:
                continue
            total_amounts = {(False, False): 0.0}
            date_next = date_min
            date_next_str = fields.Date.to_string(date_next)
            record_ind = 0
            record_prec = False
            record_prec_analytic_account = False
            record_amount = 0
            while date_next <= date_max:
                record = records[record_ind:record_ind + 1]
                analytic_account = record
                for field_name in analytic_account_field.split('.'):
                    analytic_account = analytic_account[field_name]
                if record_prec and record[date_field] == record_prec[date_field] \
                        and analytic_account == record_prec_analytic_account \
                        and record.of_analytic_section_id == record_prec.of_analytic_section_id:
                    # On continue sur la même date et la même section, on ajoute la valeur sans créer de nouvelle entrée
                    record_amount += record[amount_field] * sign
                    record_ind += 1
                    continue
                if record_prec:
                    # On a changé de date, de compte analytique ou de section,
                    #   on crée une entrée pour la valeur précédente
                    value_obj.create({
                        'analysis_id': self.id,
                        'analytic_account_id': analytic_account.id,
                        'analytic_section_id': record_prec.of_analytic_section_id.id,
                        'date': record_prec[date_field],
                        'type': value_type,
                        'amount': record_amount,
                    })
                    key = (
                        record_prec_analytic_account.id,
                        record_prec.of_analytic_section_id.id,
                    )
                    total_amounts[key] = total_amounts.get(key, 0) + record_amount
                    record_prec = False
                if record and record[date_field] < date_next_str:
                    # L'enregistrement est dans le mois en cours d'analyse, on garde les infos pour créer une entrée
                    record_prec = record
                    record_prec_analytic_account = analytic_account
                    record_amount = record[amount_field] * sign
                    record_ind += 1
                    continue
                else:
                    # Analyse du mois terminée, on peut passer au mois suivant
                    if date_next < date_max:
                        for (analytic_account_id, section_id), amount in total_amounts.iteritems():
                            value_obj.create({
                                'analytic_account_id': analytic_account_id,
                                'analytic_section_id': section_id,
                                'analysis_id': self.id,
                                'date': date_next_str,
                                'type': value_type,
                                'amount': amount,
                            })
                    date_next += relativedelta(months=1)
                    date_next_str = fields.Date.to_string(date_next)
