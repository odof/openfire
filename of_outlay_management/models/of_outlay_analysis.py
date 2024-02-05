# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from collections import defaultdict
from datetime import timedelta

from dateutil.relativedelta import relativedelta
from of_outlay_analysis_line import OUTLAY_LINE_TYPES

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

# todo: budget engagé en anglais : committed budget


class OFOutlayAnalysis(models.Model):
    _name = 'of.outlay.analysis'
    _description = u"Analyse de débours"
    _order = 'state desc, name'

    name = fields.Char(string=u"Libellé")
    analytic_account_ids = fields.Many2many(
        comodel_name='account.analytic.account', string=u"Comptes analytiques", required=True
    )
    analytic_section_ids = fields.Many2many(
        comodel_name='of.account.analytic.section', string=u"Sections analytiques",
        help=u"Remplir ce champ pour filtrer les sections analytiques qui seront étudiées"
    )

    user_id = fields.Many2one(comodel_name='res.users', string=u"Responsable")
    create_date = fields.Datetime(string=u"Date de création", readonly=True)
    write_date = fields.Datetime(string=u"Dernière mise à jour", readonly=True)
    company_id = fields.Many2one(
        comodel_name='res.company', string=u"Société", required=True,
        default=lambda self: self.env['res.company']._company_default_get('of.outlay.analysis')
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency', related='company_id.currency_id', string=u"Devise", readonly=True
    )
    state = fields.Selection(
        selection=[('open', u"Ouvert"), ('closed', u"Fermé")], string=u"État", default='open', required=True
    )
    sales_total = fields.Float(string=u"CA", compute='_compute_sales_total', help=u"Chiffre d'affaire des CC initiales")
    expected_margin_pct = fields.Float(string=u"Marge objectif (%)")
    expected_margin = fields.Monetary(
        string=u"Marge objectif", currency_field='currency_id', compute='_compute_expected_margin')

    # Les lignes sont les valeurs affichées en vue liste dans le formulaire de l'analyse
    line_ids = fields.One2many(comodel_name='of.outlay.analysis.line', inverse_name='analysis_id', string=u"Lignes")
    # Les valeurs servent à alimenter la vue graphe (courbe) des montants au cours du temps
    value_ids = fields.One2many(comodel_name='of.outlay.analysis.value', inverse_name='analysis_id', string=u"Valeurs")

    # Objets sélectionnés (vie champs m2m_tags)
    sale_ids = fields.Many2many(
        comodel_name='sale.order', string=u"Commandes client", compute='_compute_sale_ids'
    )
    sale_init_ids = fields.Many2many(
        comodel_name='sale.order', string=u"CC initiales",
        relation='of_outlay_analysis_sale_rel', column1='analysis_id', column2='order_id',
        domain="[('project_id', 'in', analytic_account_ids and analytic_account_ids[0][2] or [])]"
    )
    sale_compl_ids = fields.Many2many(
        comodel_name='sale.order', string=u"CC complémentaires",
        relation='of_outlay_analysis_sale_compl_rel', column1='analysis_id', column2='order_id',
        domain="[('project_id', 'in', analytic_account_ids and analytic_account_ids[0][2] or [])]"
    )
    purchase_ids = fields.Many2many(
        comodel_name='purchase.order', string=u"Commandes fournisseur",
        domain="[('order_line.account_analytic_id', 'in', analytic_account_ids and analytic_account_ids[0][2] or [])]"
    )
    all_picking_ids = fields.Many2many(comodel_name='stock.picking', compute='_compute_all_picking_ids')
    picking_ids = fields.Many2many(
        comodel_name='stock.picking', string=u"Bons de livraison",
        domain="[('id', 'in', all_picking_ids and all_picking_ids[0][2] or [])]"
    )
    out_invoice_ids = fields.Many2many(
        comodel_name='account.invoice', string=u"Factures client",
        relation='of_outlay_analysis_out_invoice_rel', column1='analysis_id', column2='invoice_id',
        domain="[('type', 'in', ('out_invoice', 'out_refund')),"
               " ('invoice_line_ids.account_analytic_id', 'in',"
               "  analytic_account_ids and analytic_account_ids[0][2] or [])]"
    )
    in_invoice_ids = fields.Many2many(
        comodel_name='account.invoice', string=u"Factures fournisseur",
        relation='of_outlay_analysis_in_invoice_rel', column1='analysis_id', column2='invoice_id',
        domain="[('type', 'in', ('in_invoice', 'in_refund')),"
               " ('invoice_line_ids.account_analytic_id', 'in',"
               "  analytic_account_ids and analytic_account_ids[0][2] or [])]"
    )
    all_expense_journal_ids = fields.Many2many(comodel_name='account.journal', compute='_compute_all_journal_ids')
    all_income_journal_ids = fields.Many2many(comodel_name='account.journal', compute='_compute_all_journal_ids')
    expense_journal_ids = fields.Many2many(
        comodel_name='account.journal', string=u"Journaux (Dépenses)",
        relation='of_outlay_analysis_expense_journal_rel', column1='analysis_id', column2='journal_id',
        domain="[('id', 'in', all_expense_journal_ids and all_expense_journal_ids[0][2] or [])]"
    )
    income_journal_ids = fields.Many2many(
        comodel_name='account.journal', string=u"Journaux (Recette)",
        relation='of_outlay_analysis_income_journal_rel', column1='analysis_id', column2='journal_id',
        domain="[('id', 'in', all_income_journal_ids and all_income_journal_ids[0][2] or [])]"
    )

    # Lignes sélectionnées (via checkbox)
    sale_line_ids = fields.One2many(
        comodel_name='sale.order.line',
        compute='_compute_sale_line_ids',
        inverse='_inverse_dummy',
        string=u"Lignes de commande client",
    )
    sale_line_cost_ids = fields.One2many(
        comodel_name='sale.order.line',
        compute='_compute_sale_line_ids',
        inverse='_inverse_dummy',
        string=u"Lignes de commande client (coût)",
    )
    purchase_line_ids = fields.One2many(
        comodel_name='purchase.order.line',
        compute='_compute_purchase_line_ids',
        inverse='_inverse_dummy',
        string=u"Lignes d'achat",
    )
    in_invoice_line_ids = fields.One2many(
        comodel_name='account.invoice.line',
        compute='_compute_in_invoice_line_ids',
        inverse='_inverse_dummy',
        string=u"Lignes de facture client",
    )
    out_invoice_line_ids = fields.One2many(
        comodel_name='account.invoice.line',
        compute='_compute_out_invoice_line_ids',
        inverse='_inverse_dummy',
        string=u"Lignes de facture fournisseur",
    )
    stock_move_ids = fields.Many2many(
        comodel_name='stock.move',
        compute='_compute_stock_move_ids',
        inverse='_inverse_dummy',
        string=u"Mouvements de stock",
    )

    # Lignes saisies manuellement
    expense_entry_ids = fields.One2many(
        comodel_name='of.outlay.analysis.entry', inverse_name='analysis_id',
        string=u"Produits analytiques additionnels",
        domain=[('type', '=', 'expense')]
    )
    income_entry_ids = fields.One2many(
        comodel_name='of.outlay.analysis.entry', inverse_name='analysis_id',
        string=u"Produits analytiques additionnels",
        domain=[('type', '=', 'income')]
    )

    kanban_record_ids = fields.One2many(
        comodel_name='of.outlay.analysis.kanban.record', inverse_name='analysis_id',
        string=u"Enregistrements Kanban"
    )

    @api.depends('sale_init_ids', 'sale_compl_ids')
    def _compute_sale_ids(self):
        for analysis in self:
            analysis.sale_ids = analysis.sale_init_ids | analysis.sale_compl_ids

    @api.depends('sale_init_ids')
    def _compute_sales_total(self):
        for analysis in self:
            analysis.sales_total = sum(analysis.sale_init_ids.mapped('amount_untaxed'))

    @api.depends('sales_total', 'expected_margin_pct')
    def _compute_expected_margin(self):
        for analysis in self:
            analysis.expected_margin = analysis.sales_total * analysis.expected_margin_pct / 100.0

    @api.depends('analytic_account_ids')
    def _compute_all_picking_ids(self):
        order_obj = self.env['sale.order']
        for analysis in self:
            sale_lines = (
                order_obj.search([('project_id', 'in', analysis.analytic_account_ids.ids)]).mapped('order_line')
            )
            line_procurements = sale_lines.filtered(lambda line: not line.of_is_kit).mapped('procurement_ids')
            kit_procurements = sale_lines.filtered('of_is_kit').mapped('kit_id.kit_line_ids.procurement_ids')
            stock_moves = (line_procurements + kit_procurements).mapped('move_ids')
            analysis.all_picking_ids = stock_moves.filtered(lambda move: move.state == 'done').mapped('picking_id')

    @api.depends('analytic_account_ids')
    def _compute_all_journal_ids(self):
        invoice_obj = self.env['account.invoice']
        move_line_obj = self.env['account.move.line']
        for analysis in self:
            out_invoices = invoice_obj.search(
                [('type', 'in', ('out_invoice', 'out_refund')),
                 ('invoice_line_ids.account_analytic_id', 'in', analysis.analytic_account_ids.ids)]
            )
            in_invoices = invoice_obj.search(
                [('type', 'in', ('in_invoice', 'in_refund')),
                 ('invoice_line_ids.account_analytic_id', 'in', analysis.analytic_account_ids.ids)]
            )
            entries = move_line_obj.search(
                [('analytic_account_id', 'in', analysis.analytic_account_ids.ids),
                 ('move_id', 'not in', (out_invoices + in_invoices).mapped('move_id').ids)])
            expense_moves = entries.filtered(lambda e: e.account_id.code.startswith('6')).mapped('move_id')
            income_moves = entries.filtered(lambda e: e.account_id.code.startswith('7')).mapped('move_id')
            analysis.all_expense_journal_ids = expense_moves.mapped('journal_id')
            analysis.all_income_journal_ids = income_moves.mapped('journal_id')

    @api.depends('sale_init_ids', 'sale_compl_ids', 'analytic_account_ids')
    def _compute_sale_line_ids(self):
        for analysis in self:
            sale_lines = (analysis.sale_init_ids | analysis.sale_compl_ids).mapped('order_line').filtered(
                lambda line: line.of_order_project_id in analysis.analytic_account_ids
            )
            self.sale_line_ids = sale_lines
            self.sale_line_cost_ids = sale_lines

    @api.depends('purchase_ids')
    def _compute_purchase_line_ids(self):
        for analysis in self:
            analysis.purchase_line_ids = analysis.purchase_ids.mapped('order_line').filtered(
                lambda line: line.account_analytic_id in analysis.analytic_account_ids
            )

    @api.depends('in_invoice_ids')
    def _compute_in_invoice_line_ids(self):
        for analysis in self:
            analysis.in_invoice_line_ids = analysis.in_invoice_ids.mapped('invoice_line_ids').filtered(
                lambda line: line.account_analytic_id in analysis.analytic_account_ids
            )

    @api.depends('out_invoice_ids')
    def _compute_out_invoice_line_ids(self):
        for analysis in self:
            analysis.out_invoice_line_ids = analysis.out_invoice_ids.mapped('invoice_line_ids').filtered(
                lambda line: line.account_analytic_id in analysis.analytic_account_ids
            )

    @api.depends('picking_ids')
    def _compute_stock_move_ids(self):
        for analysis in self:
            analysis.stock_move_ids = analysis.picking_ids.mapped('move_lines').filtered(
                lambda move: move.state == 'done' and move.of_analytic_account_id in analysis.analytic_account_ids
            )

    @api.multi
    def _inverse_dummy(self):
        # Fonction vide, pour permettre d'avoir des champs computed éditables
        # Cependant, on traitera l'édition dans le write, plus efficace pour ne traiter que les écarts de valeurs
        # (code [(1, id, values)] pour n'avoir que les valeurs modifiées)
        pass

    @api.onchange('sale_init_ids')
    def _onchange_sale_init_ids(self):
        if self.sale_init_ids & self.sale_compl_ids:
            self.sale_compl_ids -= self.sale_init_ids

    @api.onchange('sale_compl_ids')
    def _onchange_sale_compl_ids(self):
        if self.sale_init_ids & self.sale_compl_ids:
            self.sale_init_ids -= self.sale_compl_ids

    @api.onchange('analytic_account_ids')
    def onchange_analytic_account_ids(self):
        """
        Lors de la modification des comptes comptables, on reset tous les champs M2M.
        Cela permet à la fois un calcul plus simple et rapide que de comparer le différentiel des comptes nouvellement
        ajoutés/retirés, et donne un moyen facile et rapide de reset ces données pour l'utilisateur sans rien oublier.
        """
        self.ensure_one()

        eval_dict = {
            'analytic_account_ids': self.analytic_account_ids,
            'all_expense_journal_ids': self.all_expense_journal_ids,
            'all_income_journal_ids': self.all_income_journal_ids,
            'all_picking_ids': self.all_picking_ids,
        }
        for field_name in self.get_m2m_fields_to_recompute():
            field = self._fields[field_name]
            domain = safe_eval(field.domain.replace('[0][2]', '.ids'), globals_dict=eval_dict)
            self[field_name] = self.env[field.comodel_name].search(domain)
        self.sale_compl_ids = False

    @api.model
    def create(self, vals):
        self._apply_vals_to_o2m(vals)
        analysis = super(OFOutlayAnalysis, self).create(vals)
        if analysis.sale_init_ids:
            analysis.sale_init_ids.write({'of_outlay_analysis_type': 'init'})
        if analysis.sale_compl_ids:
            analysis.sale_compl_ids.write({'of_outlay_analysis_type': 'compl'})
        return analysis

    @api.multi
    def write(self, vals):
        self._apply_vals_to_o2m(vals)
        res = super(OFOutlayAnalysis, self).write(vals)
        # cas des sale.order retirés, on leur laisse le type ?
        if 'sale_init_ids' in vals:
            sale_orders = self.mapped('sale_init_ids').filtered(lambda sale: sale.of_outlay_analysis_type != 'init')
            if sale_orders:
                sale_orders.write({'of_outlay_analysis_type': 'init'})
        if 'sale_compl_ids' in vals:
            sale_orders = self.mapped('sale_compl_ids').filtered(lambda sale: sale.of_outlay_analysis_type != 'compl')
            if sale_orders:
                sale_orders.write({'of_outlay_analysis_type': 'compl'})
        return res

    @api.multi
    def action_open(self):
        self.write({'state': 'open'})

    @api.multi
    def action_close(self):
        self.write({'state': 'close'})

    @api.multi
    def action_recompute_lines(self):
        self.ensure_one()
        line_obj = self.env['of.outlay.analysis.line']
        section_amounts = self._get_section_values()
        lines_data = self._prepare_lines_data(section_amounts)
        self.line_ids.filtered(lambda line: line.analytic_section_id.id not in section_amounts).unlink()
        lines_dict = {
            (line.analytic_section_id.id, line.type): line
            for line in self.line_ids
        }
        for data in lines_data:
            line = lines_dict.get((data['analytic_section_id'], data['type']))
            if line:
                line.write(data)
            else:
                line_obj.create(data)

    @api.multi
    def action_recompute_values(self):
        """
        Recalcul des valeurs 'of.outlay.analysis.value' (les valeurs qui apparaîtront sous forme de courbe)
        """
        self.ensure_one()
        self = self.sudo()
        value_obj = self.env['of.outlay.analysis.value']
        if not self.sale_ids:
            raise UserError(u"Vous devez renseigner au moins 1 bon de commande client")
        sale_order_lines = self.sale_line_ids.filtered('of_outlay_analysis_selected').sorted(
            key=lambda line: (line.date_order, line.order_id.project_id.id, line.of_analytic_section_id.id)
        )
        if not sale_order_lines:
            raise UserError(u"Vous devez renseigner au moins 1 bon de commande client ayant des lignes de commande")
        purchase_order_lines = self.purchase_line_ids.filtered('of_outlay_analysis_selected').sorted(
            key=lambda line: (line.date_order, line.account_analytic_id.id, line.of_analytic_section_id.id)
        )
        out_invoice_lines = self.out_invoice_line_ids.filtered('of_outlay_analysis_selected').sorted(
            key=lambda line: (line.date_invoice, line.account_analytic_id.id, line.of_analytic_section_id.id)
        )
        in_invoice_lines = self.in_invoice_line_ids.filtered('of_outlay_analysis_selected')
        all_invoice_moves = self.env['account.invoice'].search(
            [('invoice_line_ids.account_analytic_id', 'in', self.analytic_account_ids.ids)]).mapped('move_id')
        move_lines = self.env['account.move.line'].search(
            [('analytic_account_id', 'in', self.analytic_account_ids.ids),
             ('move_id', 'not in', all_invoice_moves.ids),
             ('journal_id', 'in', (self.income_journal_ids | self.expense_journal_ids).ids)]
        )
        stock_moves = self.stock_move_ids.filtered('of_outlay_analysis_selected')
        expenses = [
            {
                'amount': line.price_subtotal,
                'analytic_account': line.account_analytic_id,
                'date': line.date_invoice,
                'of_analytic_section_id': line.of_analytic_section_id,
            }
            for line in in_invoice_lines
        ] + [
            {
                'amount': line.balance * (line.account_id.code[0] == '6' or -1),
                'analytic_account': line.analytic_account_id,
                'date': line.date,
                'of_analytic_section_id': line.of_analytic_section_id,
            }
            for line in move_lines
            if line.account_id.code[:1] in ('6', '7')
        ] + [
            {
                'amount': sum(quant.qty * quant.cost for quant in line.quant_ids),
                'analytic_account': line.of_analytic_account_id,
                'date': line.date,
                'of_analytic_section_id': line.of_analytic_section_id,
            }
            for line in stock_moves
        ]
        expenses.sort(key=lambda o: (o['date'], o['analytic_account'].id, o['of_analytic_section_id'].id))

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
            expenses and expenses[-1]['date'] or False,
            fields.Date.today())
        )
        date_max += relativedelta(months=1, day=1)

        expenses.append({
            'date': fields.Date.to_string(date_max),
            'analytic_account': self.env['account.analytic.account'],
        })

        # type expense_expected : valeur saisie en dur
        date = date_min
        sale_amount = sum(sale_order_lines.mapped('price_subtotal'))
        theoretical_expenses = sale_amount * (100.0 - self.expected_margin_pct) / 100.0
        while date < date_max:
            value_obj.create({
                'analysis_id': self.id,
                'date': fields.Date.to_string(date),
                'type': 'expense_expected',
                'analytic_account_id': False,
                'analytic_section_id': False,
                'amount': theoretical_expenses,
            })
            date += relativedelta(months=1)

        for value_type, records, amount_field, analytic_account_field, date_field, in (
            ('income_expected', sale_order_lines, 'price_subtotal', 'order_id.project_id', 'date_order'),
            ('income_invoiced', out_invoice_lines, 'price_subtotal', 'account_analytic_id', 'date_invoice'),
            ('expense_ordered', purchase_order_lines, 'price_subtotal', 'account_analytic_id', 'date_order'),
            ('expense_invoiced', expenses, 'amount', 'analytic_account', 'date'),
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
                record = record and record[0]
                analytic_account = record
                for field_name in analytic_account_field.split('.'):
                    analytic_account = analytic_account[field_name]
                if record_prec and record[date_field] == record_prec[date_field] \
                        and analytic_account == record_prec_analytic_account \
                        and record['of_analytic_section_id'] == record_prec['of_analytic_section_id']:
                    # On continue sur la même date et la même section, on ajoute la valeur sans créer de nouvelle entrée
                    record_amount += record[amount_field]
                    record_ind += 1
                    continue
                if record_prec:
                    # On a changé de date, de compte analytique ou de section,
                    #   on crée une entrée pour la valeur précédente
                    value_obj.create({
                        'analysis_id': self.id,
                        'analytic_account_id': analytic_account.id,
                        'analytic_section_id': record_prec['of_analytic_section_id'].id,
                        'date': record_prec[date_field],
                        'type': value_type,
                        'amount': record_amount,
                    })
                    key = (
                        record_prec_analytic_account.id,
                        record_prec['of_analytic_section_id'].id,
                    )
                    total_amounts[key] = total_amounts.get(key, 0) + record_amount
                    record_prec = False
                if record and record[date_field] < date_next_str:
                    # L'enregistrement est dans le mois en cours d'analyse, on garde les infos pour créer une entrée
                    record_prec = record
                    record_prec_analytic_account = analytic_account
                    record_amount = record[amount_field]
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

    @api.multi
    def action_recompute_all(self):
        # Recalcul des lignes analytiques par section
        self.action_recompute_lines()
        # Recalcul des valeurs kanban
        self.env['of.outlay.analysis.kanban.record'].recompute_records(self)
        # Recalcul des valeurs du graphe
        self.action_recompute_values()

    @api.model
    def get_m2m_fields_to_recompute(self):
        return [
            'sale_init_ids', 'purchase_ids',
            'out_invoice_ids', 'in_invoice_ids',
            'expense_journal_ids', 'income_journal_ids',
            'picking_ids',
        ]

    @api.multi
    def filter_section(self, records):
        def is_section_valid(record):
            return record[section_field_name] in self.analytic_section_ids
        self.ensure_one()
        if not self.analytic_section_ids:
            return records
        section_field_name = (
            'analytic_section_id' if 'analytic_section_id' in records._fields else 'of_analytic_section_id'
        )
        return records.filtered(is_section_valid)

    # A supprimer ? ne semble jamais appelée
    @api.multi
    def _get_initial_section_lines(self, section_id):
        self.ensure_one()
        return {
            line_type: {
                'analysis_id': self.id,
                'analytic_section_id': section_id,
                'type': line_type,
                'amount_init': 0.0,
                'amount_studies': 0.0,
                'amount_engaged': 0.0,
                'amount_current': 0.0,
                'amount_invoiced': 0.0,
                'amount_final': 0.0,
            }
            for line_type in OUTLAY_LINE_TYPES
        }

    @api.multi
    def _get_section_values(self):
        """
        Cette fonction retourne un dictionnaire des différentes valeurs nécessaires par section pour générer
        les lignes d'analyse
        """
        def get_section_amounts(analytic_section_id):
            if self.analytic_section_ids and analytic_section_id not in self.analytic_section_ids.ids:
                return False
            if analytic_section_id not in section_amounts:
                section_amounts[analytic_section_id] = defaultdict(float)
            return section_amounts[analytic_section_id]
        analytic_accounts = self.analytic_account_ids
        section_amounts = {}

        # Partie initialisation et montants complémentaires (revenus des commandes client)
        for order_line in self.sale_line_ids.filtered('of_outlay_analysis_selected'):
            amounts = get_section_amounts(order_line.of_analytic_section_id.id)
            if amounts is False:
                continue
            code = 'sale_price' if order_line.of_outlay_analysis_type == 'init' else 'sale_compl_price'
            amounts[code] += order_line.price_subtotal
        # Partie initialisation et montants complémentaires (coûts des commandes client)
        for order_line in self.sale_line_cost_ids.filtered('of_outlay_analysis_cost_selected'):
            amounts = get_section_amounts(order_line.of_analytic_section_id.id)
            if amounts is False:
                continue
            code = 'sale_cost' if order_line.of_outlay_analysis_type == 'init' else 'sale_compl_cost'
            amounts[code] += order_line.purchase_price * order_line.product_uom_qty
        # Partie montants engagés
        for order_line in self.purchase_line_ids.filtered('of_outlay_analysis_selected'):
            amounts = get_section_amounts(order_line.of_analytic_section_id.id)
            if amounts is False:
                continue
            amounts['purchase_price'] += order_line.price_subtotal
        # Partie facturation
        # 1 - Factures
        for line in self.out_invoice_line_ids.filtered('of_outlay_analysis_selected'):
            amounts = get_section_amounts(line.of_analytic_section_id.id)
            if amounts is False:
                continue
            amounts['sale_invoiced'] += line.price_subtotal
        for line in self.in_invoice_line_ids.filtered('of_outlay_analysis_selected'):
            amounts = get_section_amounts(line.of_analytic_section_id.id)
            if amounts is False:
                continue
            amounts['purchase_invoiced'] += line.price_subtotal
        # 2 - ODs
        all_invoice_moves = self.env['account.invoice'].search(
            [('invoice_line_ids.account_analytic_id', 'in', analytic_accounts.ids)]).mapped('move_id')
        misc_moves = self.env['account.move'].search(
            [('id', 'not in', all_invoice_moves.ids),
             ('line_ids.analytic_account_id', 'in', analytic_accounts.ids),
             ('journal_id', 'in', (self.income_journal_ids | self.expense_journal_ids).ids)]
        )
        for line in misc_moves.mapped('line_ids'):
            if line.analytic_account_id not in analytic_accounts:
                continue
            if line.account_id.code.startswith('6'):
                amounts = get_section_amounts(line.of_analytic_section_id.id)
                if amounts is False:
                    continue
                amounts['misc_expense'] += line.balance
            elif line.account_id.code.startswith('7'):
                amounts = get_section_amounts(line.of_analytic_section_id.id)
                if amounts is False:
                    continue
                amounts['misc_income'] -= line.balance
        # Partie stocks
        for stock_move in self.stock_move_ids.filtered('of_outlay_analysis_selected'):
            amounts = get_section_amounts(stock_move.of_analytic_section_id.id)
            if amounts is False:
                continue
            amounts['stock_value'] += sum(quant.qty * quant.cost for quant in stock_move.quant_ids)
        # Ajout des montants saisis manuellement
        for entry in self.income_entry_ids:
            amounts = get_section_amounts(entry.analytic_section_id.id)
            if amounts is False:
                continue
            code = 'sale_price' if entry.line_type == 'init' else 'sale_compl_price'
            amounts[code] += entry.price_subtotal
        for entry in self.expense_entry_ids:
            amounts = get_section_amounts(entry.analytic_section_id.id)
            if amounts is False:
                continue
            code = 'sale_cost' if entry.line_type == 'init' else 'sale_compl_cost'
            amounts[code] += entry.price_subtotal
        return section_amounts

    @api.multi
    def _prepare_section_lines_data(self, amounts, section_id):
        def get_line_value(line_type, field_name, default_value):
            # Retourne l'ancienne valeur si déjà existante, sinon retourne la nouvelle valeur fournie
            if existing_lines:
                return existing_lines[line_type][field_name]
            else:
                return default_value
        if not any(amounts.itervalues()):
            # Tous les montants sont à 0
            return []
        existing_lines = {
            line.type: line
            for line in self.line_ids
            if line.analytic_section_id.id == section_id
        }
        # Valeurs renseignées
        sale_init_margin = amounts['sale_price'] - amounts['sale_cost']
        sale_init_margin_pct = amounts['sale_price'] and 100.0 * sale_init_margin / amounts['sale_price']
        sale_compl_margin = amounts['sale_compl_price'] - amounts['sale_compl_cost']
        sale_compl_margin_pct = (
            amounts['sale_compl_price'] and 100.0 * sale_compl_margin / amounts['sale_compl_price']
        )
        sale_total_price = amounts['sale_price'] + amounts['sale_compl_price']
        sale_total_cost = amounts['purchase_price']
        sale_total_margin = sale_total_price - sale_total_cost
        sale_total_margin_pct = sale_total_price and 100.0 * sale_total_margin / sale_total_price
        invoice_price = amounts['sale_invoiced']
        invoice_cost = amounts['purchase_invoiced']
        misc_cost = amounts['misc_income'] - amounts['misc_expense']
        move_cost = invoice_cost + misc_cost
        move_margin = invoice_price - move_cost
        move_margin_pct = invoice_price and 100.0 * move_margin / invoice_price
        expected_invoiced = (
            move_cost / (1 - sale_total_margin_pct / 100.0) if sale_total_margin_pct != 100 else sale_total_price
        )
        amount_income_studies = get_line_value('income', 'amount_studies', sale_total_price)
        amount_expense_studies = get_line_value('expense', 'amount_studies', sale_total_cost)
        amount_income_current = get_line_value('income', 'amount_current', sale_total_price)
        amount_expense_current = get_line_value('expense', 'amount_current', sale_total_cost)
        return [
            {
                'analysis_id': self.id,
                'analytic_section_id': section_id,
                'type': 'income',
                'amount_init': amounts['sale_price'],
                'amount_compl': amounts['sale_compl_price'],
                'amount_studies': amount_income_studies,
                'amount_engaged': sale_total_price,
                'amount_current': amount_income_current,
                'progress_pct': sale_total_price and invoice_price / sale_total_price,
                'amount_invoiced': invoice_price,
                'amount_final': invoice_price,
            },
            {
                'analysis_id': self.id,
                'analytic_section_id': section_id,
                'type': 'expense',
                'amount_init': amounts['sale_cost'],
                'amount_compl': amounts['sale_compl_cost'],
                'amount_studies': amount_expense_studies,
                'amount_engaged': sale_total_cost,
                'amount_current': amount_expense_current,
                'progress_pct': sale_total_cost and invoice_cost / sale_total_cost,
                'amount_invoiced': invoice_cost,
                'amount_final': invoice_cost,
            },
            {
                'analysis_id': self.id,
                'analytic_section_id': section_id,
                'type': 'stock',
                'amount_studies': get_line_value('stock', 'amount_studies', 0.0),
                'amount_engaged': amounts['stock_value'],
                'amount_current': get_line_value('stock', 'amount_current', 0.0),
                'amount_invoiced': amounts['stock_value'],
                'amount_final': amounts['stock_value'],
            },
            {
                'analysis_id': self.id,
                'analytic_section_id': section_id,
                'type': 'misc',
                'amount_invoiced': misc_cost,
                'amount_final': misc_cost,
            },
            {
                'analysis_id': self.id,
                'analytic_section_id': section_id,
                'type': 'margin_theoretical',
                'amount_init': sale_init_margin,
                'amount_compl': sale_compl_margin,
                'amount_studies': amount_income_studies * sale_total_margin_pct / 100.0,
                'amount_engaged': sale_total_price * sale_total_margin_pct / 100.0,
                'amount_current': amount_income_current * sale_total_margin_pct / 100.0,
                'amount_invoiced': invoice_price * sale_total_margin_pct / 100.0,
                'amount_final': invoice_price * sale_total_margin_pct / 100.0,
                'amount_init_pct': sale_init_margin_pct,
                'amount_compl_pct': sale_compl_margin_pct,
                'amount_studies_pct': sale_total_margin_pct,
                'amount_engaged_pct': sale_total_margin_pct,
                'amount_current_pct': sale_total_margin_pct,
                'progress_pct': sale_total_price and move_cost / (1 - sale_total_margin_pct) / sale_total_price,
                'amount_invoiced_pct': sale_total_margin_pct,
                'amount_final_pct': sale_total_margin_pct,
            },
            {
                'analysis_id': self.id,
                'analytic_section_id': section_id,
                'type': 'margin_objective',
                'amount_init':
                    amounts['sale_price']
                    * get_line_value('margin_objective', 'amount_init_pct', self.expected_margin_pct) / 100.0,
                'amount_compl':
                    amounts['sale_compl_price']
                    * get_line_value('margin_objective', 'amount_compl_pct', self.expected_margin_pct) / 100.0,
                'amount_studies':
                    amount_income_studies
                    * get_line_value('margin_objective', 'amount_studies_pct', self.expected_margin_pct) / 100.0,
                'amount_engaged':
                    sale_total_price
                    * get_line_value('margin_objective', 'amount_engaged_pct', self.expected_margin_pct) / 100.0,
                'amount_current':
                    amount_income_current
                    * get_line_value('margin_objective', 'amount_current_pct', self.expected_margin_pct) / 100.0,
                'amount_invoiced':
                    invoice_price
                    * get_line_value('margin_objective', 'amount_invoiced_pct', self.expected_margin_pct) / 100.0,
                'amount_final':
                    invoice_price
                    * get_line_value('margin_objective', 'amount_final_pct', self.expected_margin_pct) / 100.0,
                'amount_init_pct':
                    get_line_value('margin_objective', 'amount_init_pct', self.expected_margin_pct),
                'amount_compl_pct':
                    get_line_value('margin_objective', 'amount_compl_pct', self.expected_margin_pct),
                'amount_studies_pct':
                    get_line_value('margin_objective', 'amount_studies_pct', self.expected_margin_pct),
                'amount_engaged_pct':
                    get_line_value('margin_objective', 'amount_engaged_pct', self.expected_margin_pct),
                'amount_current_pct':
                    get_line_value('margin_objective', 'amount_current_pct', self.expected_margin_pct),
                'progress_pct':
                    sale_total_price
                    and (
                        move_cost
                        / (1 - get_line_value('margin_objective', 'amount_engaged_pct', self.expected_margin_pct))
                    ) / sale_total_price,
                'amount_invoiced_pct':
                    get_line_value('margin_objective', 'amount_invoiced_pct', self.expected_margin_pct),
                'amount_final_pct':
                    get_line_value('margin_objective', 'amount_final_pct', self.expected_margin_pct),
            },
            {
                'analysis_id': self.id,
                'analytic_section_id': section_id,
                'type': 'margin_real',
                'amount_engaged': sale_total_margin,
                'amount_current': sale_total_margin,
                'amount_invoiced': move_margin,
                'amount_final': move_margin,
                'amount_engaged_pct': sale_total_margin_pct,
                'amount_current_pct': sale_total_margin_pct,
                'progress_pct': sale_total_price and expected_invoiced / sale_total_price,
                'amount_invoiced_pct': move_margin_pct,
                'amount_final_pct': move_margin_pct,
            },
            {
                'analysis_id': self.id,
                'analytic_section_id': section_id,
                'type': 'income_expected',
                'amount_invoiced': expected_invoiced,
            },
            {
                'analysis_id': self.id,
                'analytic_section_id': section_id,
                'type': 'to_invoice',
                'amount_invoiced': expected_invoiced - invoice_price,
            },
            {
                'analysis_id': self.id,
                'analytic_section_id': section_id,
                'type': 'expense_remaining',
                'amount_final': move_margin,
            },
        ]

    @api.multi
    def _prepare_lines_data(self, section_amounts):
        """
        Recalcul des valeurs 'of.outlay.analysis.value' (les valeurs qui apparaîtront sous forme de liste)
        """
        result = []
        ordered_section_ids = self.env['of.account.analytic.section'].search([('id', 'in', section_amounts.keys())]).ids
        if False in section_amounts:
            ordered_section_ids.append(False)
        for section_id in ordered_section_ids:
            result += self._prepare_section_lines_data(section_amounts[section_id], section_id)
        return result

    @api.model
    def _apply_vals_to_o2m(self, vals):
        o2m_related_fields = (
            'sale_line_ids', 'sale_line_cost_ids',
            'purchase_line_ids', 'stock_move_ids',
            'in_invoice_line_ids', 'out_invoice_line_ids',
        )
        editable_fields = (
            'of_outlay_analysis_selected', 'of_outlay_analysis_cost_selected', 'of_analytic_section_id'
        )
        for field_name in o2m_related_fields:
            obj = self.env[self._fields[field_name].comodel_name]
            for row in vals.pop(field_name, []):
                if row[0] != 1:
                    continue
                record_vals = {}
                for field_name in editable_fields:
                    if field_name in row[2]:
                        record_vals[field_name] = row[2][field_name]
                if record_vals:
                    obj.browse(row[1]).write(record_vals)
