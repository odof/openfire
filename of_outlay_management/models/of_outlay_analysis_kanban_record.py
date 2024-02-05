# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

RECORD_TYPES = [
    ('01_income', u"Produits"),
    ('02_expense', u"Charges"),
    ('03_gross_margin', u"Marge brute"),
    ('04_time', u"Temps"),
    ('05_net_margin', u"Marge nette"),
]

RECORD_CATEGORIES = [
    ('01_initial', u"Budget initial"),
    ('02_complementary', u"Budget complémentaire"),
    ('03_involved', u"Budget engagé"),
    ('04_current', u"Situation en cours et avancement"),
    ('05_invoiced', u"Facturé"),
]


class OFOutlayAnalysisKanbanRecord(models.Model):
    _name = 'of.outlay.analysis.kanban.record'
    _description = u"Enregistrement Kanban pour l'analyse de débours"
    _order = 'category, type'

    analysis_id = fields.Many2one(
        comodel_name='of.outlay.analysis', string=u"Analyse de débours", required=True, ondelete='cascade')
    type = fields.Selection(selection=RECORD_TYPES, string=u"Type", required=True)
    category = fields.Selection(selection=RECORD_CATEGORIES, string=u"Catégorie", required=True, readonly=True)
    value1 = fields.Char(string=u"Valeur 1")
    value2 = fields.Char(string=u"Valeur 2")
    value3 = fields.Char(string=u"Valeur 3")
    value4 = fields.Char(string=u"Valeur 4")
    label1 = fields.Char(string=u"Libellé 1")
    label2 = fields.Char(string=u"Libellé 2")
    label3 = fields.Char(string=u"Libellé 3")
    label4 = fields.Char(string=u"Libellé 4")
    main_color = fields.Char(string=u"Couleur principale")
    color1 = fields.Char(string=u"Couleur 1", default="#000000")
    color2 = fields.Char(string=u"Couleur 2", default="#000000")
    color3 = fields.Char(string=u"Couleur 3", default="#000000")
    color4 = fields.Char(string=u"Couleur 4", default="#000000")

    @api.model
    def format_number(self, amount, lang, currency=False):
        code = '%.2f' if amount % 1 else '%i'
        amount_txt = lang.format(code, amount, grouping=True)
        if not currency:
            return amount_txt
        elif currency.position == 'before':
            return currency.symbol + amount_txt
        else:
            return amount_txt + currency.symbol

    @api.model
    def recompute_records(self, analysis):
        analysis_line_obj = self.env['of.outlay.analysis.line']
        lang = self.env['res.lang'].search([('code', '=', self.env.context.get('lang', 'fr_FR'))])
        currency = analysis.currency_id

        # Delete existing records
        analysis.kanban_record_ids.unlink()

        # On réutilise les calculs faits par section pour plus d'efficacité
        # Note: on devra quand-même recalculer les valeurs pour les commandes d'achat/vente à cause des
        #  filtres supplémentaires par type d'article
        analysis_lines = {
            select[0]: analysis_line_obj for select in analysis_line_obj._fields['type'].selection
        }
        for line in analysis.line_ids:
            analysis_lines[line.type] += line
        analysis_lines['all_expense'] = analysis_lines['expense'] + analysis_lines['stock'] + analysis_lines['misc']

        # Calculs
        # [lignes, lignes initiales, lignes complémentaires]
        lines = analysis.filter_section(analysis.sale_line_ids.filtered('of_outlay_analysis_selected'))
        sale_lines = [
            lines,
            lines.filtered(lambda line: line.of_outlay_analysis_type == 'init'),
            lines.filtered(lambda line: line.of_outlay_analysis_type == 'compl')
        ]
        sale_totals = [sum(lines.mapped('price_subtotal')) for lines in sale_lines]
        lines = analysis.filter_section(analysis.sale_line_ids.filtered('of_outlay_analysis_cost_selected'))
        sale_cost_lines = [
            lines,
            lines.filtered(lambda line: line.of_outlay_analysis_type == 'init'),
            lines.filtered(lambda line: line.of_outlay_analysis_type == 'compl')
        ]
        sale_cost_totals = [
            sum(line.purchase_price * line.product_uom_qty for line in cost_lines)
            for cost_lines in sale_cost_lines
        ]
        # Saisies analytiques manuelles
        entries = analysis.filter_section(analysis.income_entry_ids)
        income_entries = [
            entries,
            entries.filtered(lambda line: line.line_type == 'init'),
            entries.filtered(lambda line: line.line_type == 'compl'),
        ]
        entries = analysis.filter_section(analysis.expense_entry_ids)
        expense_entries = [
            entries,
            entries.filtered(lambda line: line.line_type == 'init'),
            entries.filtered(lambda line: line.line_type == 'compl'),
        ]
        for i in xrange(3):
            sale_totals[i] += sum(income_entries[i].mapped('price_subtotal'))
            sale_cost_totals[i] += sum(expense_entries[i].mapped('price_subtotal'))

        # Initial budget
        init_budget_categ = '01_initial'
        init_budget_color = '#0ca789'
        self.create({
            'analysis_id': analysis.id,
            'type': '01_income',
            'category': init_budget_categ,
            'main_color': init_budget_color,
            'value1': self.format_number(sale_totals[1], lang, currency=currency),
            'label3': u"Dont produits :",
            'value3': self.format_number(
                sum(sale_lines[1].filtered(lambda line: line.product_id.type != 'service').mapped('price_subtotal'))
                +
                sum(income_entries[1].filtered(lambda line: line.product_id.type != 'service')
                    .mapped('price_subtotal')),
                lang, currency=currency),
            'label4': u"Dont services :",
            'value4': self.format_number(
                sum(sale_lines[1].filtered(lambda line: line.product_id.type == 'service').mapped('price_subtotal'))
                +
                sum(income_entries[1].filtered(lambda line: line.product_id.type == 'service')
                    .mapped('price_subtotal')),
                lang, currency=currency),
        })
        self.create({
            'analysis_id': analysis.id,
            'type': '02_expense',
            'category': init_budget_categ,
            'main_color': init_budget_color,
            'value1': self.format_number(sale_cost_totals[1], lang, currency=currency),
            'label3': u"Dont achats :",
            'value3': self.format_number(
                sum(line.purchase_price * line.product_uom_qty
                    for line in sale_cost_lines[1].filtered(lambda line: line.product_id.type != 'service'))
                +
                sum(expense_entries[1].filtered(lambda line: line.product_id.type != 'service')
                    .mapped('price_subtotal')),
                lang, currency=currency),
            'label4': u"Dont services :",
            'value4': self.format_number(
                sum(line.purchase_price * line.product_uom_qty
                    for line in sale_cost_lines[1].filtered(lambda line: line.product_id.type == 'service'))
                +
                sum(expense_entries[1].filtered(lambda line: line.product_id.type == 'service')
                    .mapped('price_subtotal')),
                lang, currency=currency),
        })
        self.create({
            'analysis_id': analysis.id,
            'type': '03_gross_margin',
            'category': init_budget_categ,
            'main_color': init_budget_color,
            'label1': u"Réelle",
            'value1':
                self.format_number(
                    sale_totals[1] and 100.0 * (sale_totals[1] - sale_cost_totals[1]) / sale_totals[1], lang)
                + u" %",
            'label2': u"Obj.",
            'value2': self.format_number(analysis.expected_margin_pct, lang) + u" %",
            'label3': u"Réelle :",
            'value3': self.format_number(sale_totals[1] - sale_cost_totals[1], lang, currency=currency),
            'label4': u"Obj. :",
            'value4': self.format_number(analysis.expected_margin, lang, currency=currency),
        })

        # Complementary budget
        compl_budget_categ = '02_complementary'
        compl_budget_color = '#3db9a1'
        self.create({
            'analysis_id': analysis.id,
            'type': '01_income',
            'category': compl_budget_categ,
            'main_color': compl_budget_color,
            'value1': self.format_number(sale_totals[2], lang, currency=currency),
            'label3': u"Dont produits :",
            'value3': self.format_number(
                sum(sale_lines[2].filtered(lambda line: line.product_id.type != 'service').mapped('price_subtotal'))
                +
                sum(income_entries[2].filtered(lambda line: line.product_id.type != 'service')
                    .mapped('price_subtotal')),
                lang, currency=currency),
            'label4': u"Dont services :",
            'value4': self.format_number(
                sum(sale_lines[2].filtered(lambda line: line.product_id.type == 'service').mapped('price_subtotal'))
                +
                sum(income_entries[2].filtered(lambda line: line.product_id.type == 'service')
                    .mapped('price_subtotal')),
                lang, currency=currency),
        })
        self.create({
            'analysis_id': analysis.id,
            'type': '02_expense',
            'category': compl_budget_categ,
            'main_color': compl_budget_color,
            'value1': self.format_number(sale_cost_totals[2], lang, currency=currency),
            'label3': u"Dont achats :",
            'value3': self.format_number(
                sum(line.purchase_price * line.product_uom_qty
                    for line in sale_cost_lines[2].filtered(lambda line: line.product_id.type != 'service'))
                +
                sum(expense_entries[2].filtered(lambda line: line.product_id.type != 'service')
                    .mapped('price_subtotal')),
                lang, currency=currency),
            'label4': u"Dont services :",
            'value4': self.format_number(
                sum(line.purchase_price * line.product_uom_qty
                    for line in sale_cost_lines[2].filtered(lambda line: line.product_id.type == 'service'))
                +
                sum(expense_entries[2].filtered(lambda line: line.product_id.type == 'service')
                    .mapped('price_subtotal')),
                lang, currency=currency),
        })
        self.create({
            'analysis_id': analysis.id,
            'type': '03_gross_margin',
            'category': compl_budget_categ,
            'main_color': compl_budget_color,
            'label1': u"Réelle",
            'value1':
                self.format_number(
                    sale_totals[2] and 100.0 * (sale_totals[2] - sale_cost_totals[2]) / sale_totals[2], lang)
                + u" %",
            'label2': u"Obj.",
            'value2': self.format_number(analysis.expected_margin_pct, lang) + u" %",
            'label3': u"Réelle :",
            'value3': self.format_number(sale_totals[2] - sale_cost_totals[2], lang, currency=currency),
            'label4': u"Obj. :",
            'value4': self.format_number(analysis.expected_margin, lang, currency=currency),
        })

        # Involved budget
        inv_budget_categ = '03_involved'
        inv_budget_color = '#85d3c4'
        self.create({
            'analysis_id': analysis.id,
            'type': '01_income',
            'category': inv_budget_categ,
            'main_color': inv_budget_color,
            'value1': self.format_number(sale_totals[0], lang, currency=currency),
            'label3': u"Dont produits :",
            'value3': self.format_number(
                sum(sale_lines[0].filtered(lambda line: line.product_id.type != 'service').mapped('price_subtotal'))
                +
                sum(income_entries[0].filtered(lambda line: line.product_id.type != 'service')
                    .mapped('price_subtotal')),
                lang, currency=currency),
            'label4': u"Dont services :",
            'value4': self.format_number(
                sum(sale_lines[0].filtered(lambda line: line.product_id.type == 'service').mapped('price_subtotal'))
                +
                sum(income_entries[0].filtered(lambda line: line.product_id.type == 'service')
                    .mapped('price_subtotal')),
                lang, currency=currency),
        })
        self.create({
            'analysis_id': analysis.id,
            'type': '02_expense',
            'category': inv_budget_categ,
            'main_color': inv_budget_color,
            'value1': self.format_number(sale_cost_totals[0], lang, currency=currency),
            'label3': u"Dont achats :",
            'value3': self.format_number(
                sum(line.purchase_price * line.product_uom_qty
                    for line in sale_cost_lines[0].filtered(lambda line: line.product_id.type != 'service'))
                +
                sum(expense_entries[0].filtered(lambda line: line.product_id.type != 'service')
                    .mapped('price_subtotal')),
                lang, currency=currency),
            'label4': u"Dont stock consommé :",
            'value4': self.format_number(
                sum(analysis_lines['stock'].mapped('amount_engaged')),
                lang, currency=currency),
        })
        self.create({
            'analysis_id': analysis.id,
            'type': '03_gross_margin',
            'category': inv_budget_categ,
            'main_color': inv_budget_color,
            'label1': u"Réelle",
            'value1':
                self.format_number(
                    sale_totals[0] and 100.0 * (sale_totals[0] - sale_cost_totals[0]) / sale_totals[0], lang)
                + u" %",
            'label2': u"Obj.",
            'value2': self.format_number(analysis.expected_margin_pct, lang) + u" %",
            'label3': u"Réelle :",
            'value3': self.format_number(sale_totals[0] - sale_cost_totals[0], lang, currency=currency),
            'label4': u"Obj. :",
            'value4': self.format_number(analysis.expected_margin, lang, currency=currency),
        })

        # Current situation
        income_current = sum(analysis_lines['income'].mapped('amount_current'))
        expense_current = sum(analysis_lines['all_expense'].mapped('amount_current'))
        expense_engaged = sum(
            line.amount_engaged if line.is_closed else line.amount_init + line.amount_compl
            for line in analysis_lines['expense']
        )
        curr_situation_categ = '04_current'
        curr_situation_color = '#fef9a2'
        self.create({
            'analysis_id': analysis.id,
            'type': '01_income',
            'category': curr_situation_categ,
            'main_color': curr_situation_color,
            'value1': self.format_number(income_current, lang, currency=currency),
            'label2': u"Fact. théo.",
            'value2': self.format_number(
                sum(analysis_lines['income_expected'].mapped('amount_invoiced')),
                lang, currency=currency),
            'label3': u"Avancement :",
            'value3': self.format_number(sale_totals[0] and 100 * income_current / sale_totals[0], lang) + u" %",
        })
        self.create({
            'analysis_id': analysis.id,
            'type': '02_expense',
            'category': curr_situation_categ,
            'main_color': curr_situation_color,
            'value1': self.format_number(expense_current, lang, currency=currency),
            'label3': u"Avancement :",
            'value3': self.format_number(expense_engaged and 100 * expense_current / expense_engaged, lang) + u" %",
        })
        self.create({
            'analysis_id': analysis.id,
            'type': '03_gross_margin',
            'category': curr_situation_categ,
            'main_color': curr_situation_color,
            'label1': u"Réelle",
            'value1':
                self.format_number(
                    income_current and 100.0 * (income_current - expense_current) / income_current, lang)
                + u" %",
            'label2': u"Obj.",
            'value2': self.format_number(analysis.expected_margin_pct, lang) + u" %",
            'label3': u"Réelle :",
            'value3': self.format_number(income_current - expense_current, lang, currency=currency),
            'label4': u"Obj. :",
            'value4': self.format_number(analysis.expected_margin, lang, currency=currency),
        })

        # Invoiced
        income_invoiced = sum(analysis_lines['income'].mapped('amount_invoiced'))
        expense_invoiced = sum(analysis_lines['all_expense'].mapped('amount_invoiced'))
        margin_real_invoiced = sum(analysis_lines['margin_real'].mapped('amount_invoiced'))
        margin_obj_invoiced = sum(analysis_lines['margin_objective'].mapped('amount_invoiced'))

        invoiced_categ = '05_invoiced'
        invoiced_color = '#b6e4db'
        self.create({
            'analysis_id': analysis.id,
            'type': '01_income',
            'category': invoiced_categ,
            'main_color': invoiced_color,
            'label1': u"À date",
            'value1': self.format_number(income_invoiced, lang, currency=currency),
            'label2': u"FAE",
            'value2': self.format_number(
                sum(analysis_lines['to_invoice'].mapped('amount_invoiced')),
                lang, currency=currency),
            'label3': u"Avancement :",
            'value3': self.format_number(
                sale_totals[0] and 100 * income_invoiced / sale_totals[0], lang, currency=currency),
        })
        self.create({
            'analysis_id': analysis.id,
            'type': '02_expense',
            'category': invoiced_categ,
            'main_color': invoiced_color,
            'label1': u"À date",
            'value1': self.format_number(expense_invoiced, lang, currency=currency),
            'label2': u"Gap",
            'value2': self.format_number(sale_cost_totals[0] - expense_invoiced, lang, currency=currency),
            'label3': u"Avancement :",
            'value3': self.format_number(
                expense_engaged and 100 * expense_invoiced / expense_engaged, lang, currency=currency),
        })
        self.create({
            'analysis_id': analysis.id,
            'type': '03_gross_margin',
            'category': invoiced_categ,
            'main_color': invoiced_color,
            'label1': u"Réelle",
            'value1':
                self.format_number(income_invoiced and 100 * margin_real_invoiced / income_invoiced, lang) + u" %",
            'label2': u"Obj.",
            'value2': self.format_number(analysis.expected_margin_pct, lang) + u" %",
            'label3': u"Réelle :",
            'value3': self.format_number(margin_real_invoiced, lang, currency=currency),
            'label4': u"Obj. :",
            'value4': self.format_number(margin_obj_invoiced, lang, currency=currency),
        })
