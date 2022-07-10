# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

import odoo.addons.decimal_precision as dp
from datetime import date
import time
import base64


class OfWizardSituation(models.TransientModel):
    _name = "of.wizard.situation"

    partner_id = fields.Many2one(comodel_name='res.partner', string=u"Client")
    order_id = fields.Many2one(comodel_name='sale.order', string=u"Commande client")
    company_id = fields.Many2one(comodel_name='res.company', string=u"Société")
    line_ids = fields.One2many(
        comodel_name='of.wizard.situation.line', inverse_name='situation_id', string=u"Lignes de situation")

    amount_next_ht = fields.Float(
        compute='_compute_amounts', digits=dp.get_precision('Product Price'), string=u"Montant total",
        help=u"Montant total facturé au client à la prochaine situation, incluant les situations précédentes")
    amount_invoiced_ht = fields.Float(
        compute='_compute_amounts', digits=dp.get_precision('Product Price'), string=u'Montant déjà facturé')
    amount_to_invoice_ht = fields.Float(
        compute='_compute_amounts', multi='amount',
        digits=dp.get_precision('Product Price'), string=u"Montant de situation")
    amount_next_ttc = fields.Float(
        compute='_compute_amounts', multi='amount', digits=dp.get_precision('Product Price'), string=u"Montant total",
        help=u"Montant total facturé au client à la prochaine situation, incluant les situations précédentes")
    amount_invoiced_ttc = fields.Float(
        compute='_compute_amounts', multi='amount',
        digits=dp.get_precision('Product Price'), string=u"Montant déjà facturé")
    amount = fields.Float(
        compute='_compute_amounts', multi='amount',
        digits=dp.get_precision('Product Price'), string=u"Montant de situation")

    prochaine_situation = fields.Integer(
        string=u"Situation en cours", related='order_id.of_prochaine_situation', readonly=True)
    date_rapport_situation = fields.Date(
        string=u"Date rapport situation", required=True, default=lambda self: time.strftime('%Y-%m-%d'))

    def _compute_amounts(self):
        product_situation_id = self.env['ir.values'].get_default(
            'sale.config.settings', 'of_product_situation_id_setting')
        product_situation = self.env['product.product'].browse(product_situation_id)
        for wizard in self:
            order = wizard.order_id
            cur = order.currency_id
            round_globally = order.company_id.tax_calculation_rounding_method == 'round_globally'

            # tableau de valeurs HT, TVA, TTC pour les situations totale à venir, totale facturée, différentielle
            values = [[0.0]*3 for _ in xrange(3)]
            # situation_only=False car on veut l'information du total déjà facturé, situations ET acomptes
            for tax, amounts in wizard.get_situation_amounts(situation_only=False).iteritems():
                for i, amount in enumerate(amounts + [amounts[0] - amounts[1]]):
                    taxes = tax.compute_all(
                        amount, cur, 1.0, product=product_situation, partner=order.partner_shipping_id)

                    if round_globally:
                        price_tax = sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                    else:
                        price_tax = taxes['total_included'] - taxes['total_excluded']
                    values[i][0] += taxes['total_excluded']
                    values[i][1] += price_tax

            for vals in values:
                vals[0] = cur.round(vals[0])
                vals[1] = cur.round(vals[1])
                vals[2] = cur.round(vals[0] + vals[1])

            wizard.amount_next_ht = values[0][0]
            wizard.amount_next_ttc = values[0][2]
            wizard.amount_invoiced_ht = values[1][0]
            wizard.amount_invoiced_ttc = values[1][2]
            wizard.amount_to_invoice_ht = values[2][0]
            wizard.amount = values[2][2]

    @api.multi
    def name_get(self):
        return [(record.id, "Situation n°%i" % record.prochaine_situation) for record in self]

    def action_dummy(self):
        return True

    @api.multi
    def get_situation_amounts(self, situation_only=True):
        """
        @param situation_only: Si vrai, ne traite que les lignes de factures avec l'article de situation.
                               Si faux, traite toutes les lignes de facture hors lignes de prorata,
                               retenue de garantie et acomptes
        @return: Dictionnaire {taxes : [montant_total , montant_déjà_facturé]}
        """
        order = self.order_id
        cur = order.pricelist_id.currency_id
        # Format de result : {[tax_ids]: [tax_amount, total_untaxed, invoiced_untaxed]}
        result = {}
        if situation_only:
            product_situation_id = self.env['ir.values'].get_default(
                'sale.config.settings', 'of_product_situation_id_setting')

            def is_valid_line(invoice_line):
                return invoice_line.product_id.id == product_situation_id
        else:
            product_prorata_id = self.env['ir.values'].get_default(
                'sale.config.settings', 'of_product_prorata_id_setting')
            product_retenue_id = self.env['ir.values'].get_default(
                'sale.config.settings', 'of_product_retenue_id_setting')
            acompte_categ_id = self.env['ir.values'].get_default(
                'sale.config.settings', 'of_deposit_product_categ_id_setting')

            def is_valid_line(invoice_line):
                return invoice_line.product_id.id not in (product_prorata_id, product_retenue_id)\
                    and invoice_line.product_id.categ_id.id != acompte_categ_id

        # Récupération des montants voulus, par taxe
        for line in self.line_ids:
            # Remplissage des taxes et du montant total HT
            result.setdefault(line.tax_id, [0.0, 0.0])[0] += line.price_subtotal * line.sit_val_suiv / 100.0

        # Récupération des montants déjà facturés
        for invoice in order.invoice_ids:
            if invoice.state == 'cancel':
                continue
            for line in invoice.invoice_line_ids:
                if is_valid_line(line):
                    result.setdefault(line.invoice_line_tax_ids, [0.0, 0.0])[1] += line.price_subtotal_signed

        for amounts in result.itervalues():
            amounts[0] = cur.round(amounts[0])
            amounts[1] = cur.round(amounts[1])
        return result

    @api.multi
    def action_prefill(self):
        self.ensure_one()
        context = {
            'default_situation_id': self.id,
        }
        action = {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'of.wizard.situation.prefill',
            'target': 'new',
            'context': context,
        }
        return action

    @api.multi
    def action_make_invoice(self):
        """ Génère la prochaine facture de situation.
        @return: Factures générées
        """
        self.ensure_one()
        order_line_obj = self.env['sale.order.line']
        invoice_line_obj = self.env['account.invoice.line']
        report_obj = self.env['report']
        order = self.order_id
        situation_number = self.prochaine_situation

        product_situation_id = self.env['ir.values'].get_default(
            'sale.config.settings', 'of_product_situation_id_setting')
        if not product_situation_id:
            raise UserError(u"Vous devez définir l'Article de situation dans la configuration des ventes.")
        product_situation = self.env['product.product'].browse(product_situation_id)

        # --- Calcul des montants de situation à facturer par taxe ---
        for line in self.line_ids:
            if line.sit_val_suiv > 100:
                raise UserError(u"Le total des situations ne doit pas dépasser 100%%.\n\n%s" % line.order_line_id.name)

        # --- Génération du rapport de situation ---
        pdf = report_obj.sudo().get_pdf([self.id], 'of_sale_prorata.of_report_situation')
        filename = _('Rapport de situation n°%s') % situation_number

        # --- Création de la facture ---
        invoice = self.env['account.invoice'].with_context(company_id=order.company_id.id).create({
            'origin': order.name,
            'type': 'out_invoice',
            'reference': False,
            'account_id': order.partner_id.property_account_receivable_id.id,
            'partner_id': order.partner_invoice_id.id,
            'partner_shipping_id': order.partner_shipping_id.id,
            'currency_id': order.pricelist_id.currency_id.id,
            # La position fiscale a peu d'intérêt, la taxe sera forcée par ligne. Mais on ne sait jamais.
            'fiscal_position_id': order.fiscal_position_id.id or order.partner_id.property_account_position_id.id,
            'company_id': order.company_id.id,
            'team_id': order.team_id.id,
            'user_id': order.user_id.id,
            'comment': order.note,
        })

        account_situation = invoice_line_obj.get_invoice_line_account('out_invoice', product_situation,
                                                                      order.fiscal_position_id, order.company_id)
        product_situation_name = product_situation.name_get()[0][1]
        if product_situation.description_sale:
            product_situation_name += '\n' + product_situation.description_sale

        total_untaxed = 0
        # situation_only=True car les factures d'acompte sont gérées automatiquement.
        # On ne veut pas les traiter une seconde fois.
        for taxes, amounts in self.get_situation_amounts(situation_only=True).iteritems():
            total_untaxed += amounts[0]
            amount = amounts[0] - amounts[1]
            if not amount:
                continue

            # --- Création des lignes de commande ---
            so_line = order_line_obj.create({
                'name': _('Situation n°%s : %s') % (situation_number, time.strftime('%m %Y'),),
                'price_unit': amount,
                'product_uom_qty': 0.0,
                'order_id': order.id,
                'discount': 0.0,
                'product_uom': product_situation.uom_id.id,
                'product_id': product_situation.id,
                'tax_id': [(6, 0, taxes._ids)],
            })

            # --- Création des lignes de facture ---
            account = account_situation
            for tax in taxes:
                account = tax.map_account(account)

            invoice_line_obj.create({
                'invoice_id': invoice.id,
                'name': product_situation_name,
                'origin': order.name,
                'account_id': account.id,
                'price_unit': amount,
                'quantity': 1.0,
                'discount': 0.0,
                'uom_id': product_situation.uom_id.id,
                'product_id': product_situation.id,
                'sale_line_ids': [(6, 0, [so_line.id])],
                'invoice_line_tax_ids': [(6, 0, taxes._ids)],
                'account_analytic_id': order.project_id.id or False,
            })

        # --- Ajout de la retenue de garantie, le cas échéant ---
        # La retenue de garantie se calcule avant l'application du prorata
        if order.of_retenue_garantie_pct:
            # La retenue de garantie se calcule sur le montant TTC, il faut donc calculer les taxes au préalable
            invoice.compute_taxes()
            invoice.of_add_retenue_line(order.of_retenue_garantie_pct, order)

        # --- Ajout de la ligne de prorata, le cas échéant ---
        if order.of_prorata_percent:
            invoice.of_add_prorata_line(order.of_prorata_percent, order)

        # --- Retranchement des acomptes déjà versés ---
        categ_acompte_id = self.env['ir.values'].get_default(
            'sale.config.settings', 'of_deposit_product_categ_id_setting')
        acompte_invoices = set()
        # Un premier parcours pour récupérer toutes les factures d'acompte.
        for line in order.order_line:
            if line.product_id.categ_id.id == categ_acompte_id and line.qty_to_invoice < 0:
                acompte_invoices.add(line.invoice_lines.mapped('invoice_id'))
        # Un second parcours pour récupérer toutes les lignes, acompte et prorata.
        for line in order.order_line:
            if line.invoice_lines.mapped('invoice_id') in acompte_invoices and line.qty_to_invoice < 0:
                line.invoice_line_create(invoice.id, line.qty_to_invoice)

        # --- Stockage du rapport de situation sur la facture ---
        self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.encodestring(pdf),
            'res_model': 'account.invoice',
            'res_id': invoice.id,
            'mimetype': 'application/x-pdf',
            'datas_fname': "%s.pdf" % filename,
        })

        invoice.compute_taxes()
        if invoice.amount_total < 0:
            raise UserError(u"Vous ne pouvez pas générer une facture de situation d'un montant négatif")
        # Alternative possible : mettre ce texte dans les notes de haut de page
        # du module OCA/sale_reporting/sale_comment_template
        invoice.name = u"Situation de travaux n°%s" % situation_number
        invoice.message_post_with_view(
            'mail.message_origin_link',
            values={'self': invoice, 'origin': order},
            subtype_id=self.env.ref('mail.mt_note').id)

        return invoice

    @api.multi
    def button_make_invoice(self):
        self.ensure_one()
        action = self.env.ref('account.action_invoice_tree1').read()[0]
        action['views'] = [(self.env.ref('account.invoice_form').id, 'form')]
        action['res_id'] = self.action_make_invoice().id
        return action

    @api.multi
    def button_layout_category_situation(self):
        self.ensure_one()
        wizard_obj = self.env['of.wizard.situation.layout.category']
        product_situation_id = self.env['ir.values']\
            .get_default('sale.config.settings', 'of_product_situation_id_setting')
        if not product_situation_id:
            raise UserError(u"Vous devez définir l'Article de situation dans la configuration des ventes.")

        wizard_lines_data = []

        # Création d'une ligne de wizard par section
        for layout_category in self.line_ids.mapped('of_layout_category_id'):
            data = (0, 0, {
                'of_layout_category_id': layout_category.id,
                'situation_line_ids': [(6, 0, self.line_ids.filtered(
                    lambda wsl: wsl.of_layout_category_id == layout_category).ids)]
            })
            wizard_lines_data.append(data)

        # Création d'une ligne de wizard si des lignes de commande n'ont pas de section
        situation_lines_without_category = self.line_ids.filtered(lambda wsl: not wsl.of_layout_category_id)
        if situation_lines_without_category:
            data = (0, 0, {
                'of_layout_category_id': False,
                'situation_line_ids': [(6, 0, situation_lines_without_category.ids)],
            })
            wizard_lines_data.append(data)

        # Création du wizard
        situation_data = {
            'situation_id': self.id,
            'order_id': self.order_id.id,
            'layout_category_ids': wizard_lines_data,
        }
        wizard = wizard_obj.create(situation_data)

        action = {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'of.wizard.situation.layout.category',
            'res_id': wizard.id,
            'target': 'new',
        }
        return action

    @api.multi
    def situation_lines_layouted(self):
        self.ensure_one()
        report_groups = []
        order_line_situation = {line.order_line_id: line for line in self.line_ids}

        for order_page in self.order_id.order_lines_layouted():
            for order_group in order_page:
                sit_lines = [order_line_situation[order_line] for order_line in order_group['lines']
                             if order_line in order_line_situation]
                if sit_lines:
                    # inhiber l'affichage de la référence
                    afficher_ref = self.env['ir.values']\
                        .get_default('sale.config.settings', 'pdf_display_product_ref_setting')

                    for line in sit_lines:
                        order_id = line.order_line_id.order_id
                        self = self.with_context(lang=order_id.partner_id.lang, partner=order_id.partner_id.id)

                        name = line.order_line_id.name
                        if not afficher_ref and name.startswith("["):
                            pos = name.find(']')
                            if pos != -1:
                                name = name[pos + 1:]
                        line.name = name.strip()

                # On ajoute une section lorsque les sections avancées sont activées ou que la section a des lignes
                if self.user_has_groups('of_sale_quote_template.group_of_advanced_sale_layout_category') or sit_lines:
                    report_groups.append({
                        'name': order_group['name'],
                        'subtotal': order_group['subtotal'],
                        'pagebreak': False,
                        'lines': sit_lines,
                        'color': order_group['color']
                    })
        return report_groups

    @api.multi
    def of_get_report_name(self, docs):
        return "Situation %s" % self.order_id.of_prochaine_situation

    @api.multi
    def of_get_report_number(self, docs):
        return self.order_id.name

    @api.multi
    def of_get_report_date(self, docs):
        lang = self.env['res.lang']._lang_get(self.env.lang or 'fr_FR')
        return date.today().strftime(lang.date_format)

    def get_color_font(self):
        return self.env['ir.values'].get_default('sale.config.settings', 'of_color_font') or "#000000"


class OfWizardSituationLine(models.TransientModel):
    _name = "of.wizard.situation.line"
    _inherits = {'sale.order.line': 'order_line_id'}

    name = fields.Char(compute='_compute_name', string=u"Description courte")
    situation_id = fields.Many2one(comodel_name='of.wizard.situation', string=u"Wizard", required=True)
    order_line_id = fields.Many2one(
        comodel_name='sale.order.line', string=u"Ligne de commande", required=True, ondelete="cascade")
    layout_category_id = fields.Many2one(
        comodel_name='sale.layout_category', related='order_line_id.layout_category_id', readonly=True)
    of_layout_category_id = fields.Many2one(
        comodel_name='of.sale.order.layout.category',
        related='order_line_id.of_layout_category_id', readonly=True)

    sit_val_n = fields.Float(compute='_compute_sit_vals', inverse='_inverse_sit_val_n', string="Sit. n (%)")
    sit_val_prec = fields.Float(compute='_compute_sit_vals', string="Total n-1 (%)")
    sit_val_suiv = fields.Float(compute='_compute_sit_val_suiv', string="Total n (%)")

    @api.depends('order_line_id.name')
    def _compute_name(self):
        for line in self:
            line.name = line.order_line_id.name.split('\r', 1)[0].split('\n', 1)[0]

    @api.depends()
    def _compute_sit_vals(self):
        for line in self:
            n = line.situation_id.prochaine_situation
            vals = {sit.situation: sit.value for sit in line.order_line_id.situation_ids}

            line.sit_val_prec = sum([val for sit, val in vals.iteritems() if sit < n])
            line.sit_val_n = vals.get(n, 0)

    @api.depends('sit_val_prec', 'sit_val_n')
    def _compute_sit_val_suiv(self):
        for line in self:
            line.sit_val_suiv = line.sit_val_prec + line.sit_val_n

    def _inverse_sit_val_n(self):
        situation_obj = self.env['of.sale.order.line.situation']
        for line in self:
            n = self.situation_id.prochaine_situation
            for sit in line.order_line_id.situation_ids:
                if sit.situation == n:
                    sit.value = line.sit_val_n
                    break
            else:
                situation_obj.create({
                    'order_line_id': line.order_line_id.id,
                    'situation': n,
                    'value': line.sit_val_n,
                })

    @api.onchange('sit_val_n')
    def _onchange_sit_val_n(self):
        for line in self:
            if line.sit_val_suiv > 100:
                line.sit_val_n = 100 - line.sit_val_prec


class OfWizardSituationLayoutCategory(models.TransientModel):
    _name = "of.wizard.situation.layout.category"

    state = fields.Selection(selection=[('step1', u"Étape 1"), ('step2', u"Étape 2")], string=u"Étape", default='step1')
    order_id = fields.Many2one(comodel_name='sale.order', string=u"Commande client")
    situation_id = fields.Many2one(comodel_name='of.wizard.situation', string=u"Wizard", required=True)
    layout_category_ids = fields.One2many(
        comodel_name='of.wizard.situation.layout.category.line',
        inverse_name='layout_category_situation_id', string=u"Lignes de situation par section")
    type = fields.Selection(
        selection=[
            ('sit_val_n', u"Sit. n (%)"),
            ('sit_val_suiv', u"Total n (%)"),
        ], string=u"Type", default='sit_val_n')
    value = fields.Float(string=u"Valeur")

    @api.multi
    def name_get(self):
        return [(record.id, "Situation par section n°%i" % record.situation_id.prochaine_situation) for record in self]

    @api.multi
    def button_prefill(self):
        self.ensure_one()
        self.state = 'step2'
        return {
            'type': 'ir.actions.do_nothing'
        }

    @api.multi
    def button_return(self):
        self.ensure_one()
        self.state = 'step1'
        return {
            'type': 'ir.actions.do_nothing'
        }

    def button_apply_prefill(self):
        for layout_category in self.layout_category_ids:
            if self.type == 'sit_val_n':
                layout_category.sit_val_n = self.value
            else:
                layout_category.sit_val_n = max(self.value, layout_category.sit_val_prec) - layout_category.sit_val_prec
            layout_category._onchange_sit_val_n()

        self.state = 'step1'
        return {
            'type': 'ir.actions.do_nothing'
        }

    @api.multi
    def button_apply(self):
        for layout_category in self.layout_category_ids:
            lines = layout_category.situation_line_ids
            amount_to_complete = layout_category.price_subtotal * (layout_category.sit_val_n / 100)
            lines_amount_due = sum(
                line.price_subtotal - line.price_subtotal * (line.sit_val_prec / 100) for line in lines)

            # Le facteur va déterminer quel pourcentage du montant restant dû de chaque ligne on va facturer
            factor = amount_to_complete / lines_amount_due if lines_amount_due else 1
            for line in lines:
                line.sit_val_n = (100 - line.sit_val_prec) * factor if line.price_subtotal else 100 - line.sit_val_prec


class OfWizardSituationLayoutCategoryLine(models.TransientModel):
    _name = "of.wizard.situation.layout.category.line"

    layout_category_situation_id = fields.Many2one(
        comodel_name='of.wizard.situation.layout.category', string=u"Wizard", required=True, ondelete="cascade")
    of_layout_category_id = fields.Many2one(
        comodel_name='of.sale.order.layout.category', string=u"Ligne de section", readonly=True)
    situation_line_ids = fields.Many2many(
        comodel_name='of.wizard.situation.line', relation='of_wizard_situation_line_layout_category_situation_rel',
        string=u"Lignes de situation", required=True)
    situation_line_count = fields.Integer(string=u"Lignes de situation", compute='_compute_situation_line_count')

    price_subtotal = fields.Float(compute='_compute_sit_vals', string="Prix HT")
    price_total = fields.Float(compute='_compute_sit_vals', string="Prix TTC")

    sit_val_n = fields.Float(string=u"Sit. n (%)")
    sit_val_prec = fields.Float(compute='_compute_sit_vals', string=u"Total n-1 (%)")
    sit_val_suiv = fields.Float(compute='_compute_sit_val_suiv', string=u"Total n (%)")

    @api.depends('situation_line_ids')
    def _compute_situation_line_count(self):
        for layout_category in self:
            layout_category.situation_line_count = len(layout_category.situation_line_ids)

    @api.depends()
    def _compute_sit_vals(self):
        for layout_category in self:
            amount_completed = 0.0
            price_subtotal = 0.0
            price_total = 0.0
            for situation_line in layout_category.situation_line_ids:
                price_subtotal += situation_line.price_subtotal
                price_total += situation_line.price_total
                amount_completed += situation_line.price_subtotal * (situation_line.sit_val_prec / 100)

            layout_category.sit_val_prec = (amount_completed / price_subtotal) * 100 if price_subtotal else 0.0
            layout_category.price_subtotal = price_subtotal
            layout_category.price_total = price_total

    @api.depends('sit_val_prec', 'sit_val_n')
    def _compute_sit_val_suiv(self):
        for layout_category in self:
            layout_category.sit_val_suiv = layout_category.sit_val_prec + layout_category.sit_val_n

    @api.onchange('sit_val_n')
    def _onchange_sit_val_n(self):
        for line in self:
            if line.sit_val_suiv > 100:
                line.sit_val_n = 100 - line.sit_val_prec


class OfWizardSituationPrefill(models.TransientModel):
    _name = "of.wizard.situation.prefill"

    situation_id = fields.Many2one(comodel_name='of.wizard.situation', string=u"Wizard", required=True)
    type = fields.Selection(
        selection=[
            ('sit_val_n', u"Sit. n (%)"),
            ('sit_val_suiv', u"Total n (%)"),
        ], string=u"Type", required=True, default='sit_val_n')
    value = fields.Float(string=u"Valeur", required=True)

    @api.multi
    def button_apply(self):
        for line in self.situation_id.line_ids:
            if self.type == 'sit_val_n':
                line.sit_val_n = self.value
            else:
                line.sit_val_n = max(self.value, line.sit_val_prec) - line.sit_val_prec
            line._onchange_sit_val_n()
