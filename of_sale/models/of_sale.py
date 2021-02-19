# -*- coding: utf-8 -*-

import itertools
import json
from odoo import models, fields, api, _
from odoo.addons.sale.models.sale import SaleOrderLine as SOL
from odoo.addons.sale.models.sale import SaleOrder as SO
from odoo.tools import float_compare, float_is_zero, DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import UserError
from odoo.models import regex_order
from odoo.addons.of_utils.models.of_utils import get_selection_label


NEGATIVE_TERM_OPERATORS = ('!=', 'not like', 'not ilike', 'not in')


@api.onchange('product_uom', 'product_uom_qty')
def product_uom_change(self):
    u"""Copie de la fonction parente avec retrait de l'affectation du prix unitaire"""
    if not self.product_uom or not self.product_id:
        self.price_unit = 0.0
        return
    if self.order_id.pricelist_id.of_is_quantity_dependent(self.product_id.id, self.order_id.date_order) \
            and self.order_id.partner_id \
            and (not self.price_unit or float_compare(self.price_unit, self.product_id.list_price, 2) != 0):
        self.price_unit = self.of_get_price_unit()


SOL.product_uom_change = product_uom_change


@api.onchange('fiscal_position_id')
def _compute_tax_id(self):
    """
    La fonction est appelée compute mais est en réalité un onchange. Surcharge pour ne pas réaffecter les taxes
    sur des lignes ayant déjà été facturées
    """
    for order in self:
        order.order_line.filtered(lambda l: not l.invoice_lines)._compute_tax_id()


SO._compute_tax_id = _compute_tax_id


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'of.documents.joints']

    def pdf_afficher_multi_echeances(self):
        return self.env['ir.values'].get_default('sale.config.settings', 'pdf_afficher_multi_echeances')

    def pdf_afficher_nom_parent(self):
        return self.env['ir.values'].get_default('sale.config.settings', 'pdf_adresse_nom_parent')

    def pdf_afficher_civilite(self):
        return self.env['ir.values'].get_default('sale.config.settings', 'pdf_adresse_civilite')

    def pdf_afficher_telephone(self):
        return self.env['ir.values'].get_default('sale.config.settings', 'pdf_adresse_telephone') or 0

    def pdf_afficher_mobile(self):
        return self.env['ir.values'].get_default('sale.config.settings', 'pdf_adresse_mobile') or 0

    def pdf_afficher_fax(self):
        return self.env['ir.values'].get_default('sale.config.settings', 'pdf_adresse_fax') or 0

    def pdf_afficher_email(self):
        return self.env['ir.values'].get_default('sale.config.settings', 'pdf_adresse_email') or 0

    def pdf_afficher_date_validite(self):
        return self.env['ir.values'].get_default('sale.config.settings', 'pdf_date_validite_devis')

    def pdf_vt_pastille(self):
        return self.env['ir.values'].get_default('sale.config.settings', 'pdf_vt_pastille')

    def pdf_hide_global_address_label(self):
        return self.env['ir.values'].get_default('sale.config.settings', 'pdf_hide_global_address_label')

    def pdf_masquer_commercial(self):
        return self.env['ir.values'].get_default('sale.config.settings', 'pdf_masquer_pastille_commercial')

    def pdf_mail_commercial(self):
        return self.env['ir.values'].get_default('sale.config.settings', 'pdf_mail_commercial')

    def pdf_masquer_payment_term(self):
        return self.env['ir.values'].get_default('sale.config.settings', 'pdf_masquer_pastille_payment_term')

    def pdf_of_pdf_taxes_display(self):
        return self.env['ir.values'].get_default('sale.config.settings', 'of_pdf_taxes_display')

    def get_color_section(self):
        return self.env['ir.values'].get_default('sale.config.settings', 'of_color_bg_section')

    def get_color_font(self):
        return self.env['ir.values'].get_default('sale.config.settings', 'of_color_font') or "#000000"

    def _search_of_to_invoice(self, operator, value):
        # Récupération des bons de commande non entièrement livrés
        self._cr.execute("SELECT DISTINCT order_id\n"
                         "FROM sale_order_line\n"
                         "WHERE qty_to_invoice + qty_invoiced < product_uom_qty")
        order_ids = self._cr.fetchall()

        domain = ['&', '&',
                  ('of_force_invoice_status', 'not in', ('invoiced', 'no')),
                  ('state', 'in', ('sale', 'done')),
                  ('order_line.qty_to_invoice', '>', 0)]
        if order_ids:
            domain = ['&'] + domain + [('id', 'not in', zip(*order_ids)[0])]
        return domain

    @api.depends('order_line.price_total')
    def _amount_all(self):
        """Compute the total amounts of the SO."""
        # Le calcul standard diffère du calcul utilisé dans les factures, cela peut mener à des écarts dans certains cas
        # (quand l'option d'arrondi global de la tva est utilisée
        # et que la commande contient plusieurs lignes avec des taxes différentes).
        # On uniformise le calcul du montant des devis/commandes avec celui des factures.
        for order in self:
            order.amount_untaxed = sum(line.price_subtotal for line in order.order_line)
            order.amount_tax = sum(tax['amount'] for tax in order.of_get_taxes_values().itervalues())
            order.amount_total = order.amount_untaxed + order.amount_tax

    of_to_invoice = fields.Boolean(
        u"Entièrement facturable", compute='_compute_of_to_invoice', search='_search_of_to_invoice'
    )
    of_notes_facture = fields.Html(string="Notes facture", oldname="of_notes_factures")
    of_notes_intervention = fields.Html(string="Notes intervention")
    of_notes_client = fields.Text(related='partner_id.comment', string="Notes client", readonly=True)

    of_total_cout = fields.Monetary(compute='_compute_of_marge', string='Prix de revient')
    of_marge_pc = fields.Float(compute='_compute_of_marge', string='Marge %')

    of_etiquette_partenaire_ids = fields.Many2many(
        'res.partner.category', related='partner_id.category_id', string=u"Étiquettes client")
    of_client_view = fields.Boolean(string='Vue client/vendeur')

    of_date_vt = fields.Date(
        string="Date visite technique", help=u"Si renseignée apparaîtra sur le devis / Bon de commande"
    )
    of_echeance_line_ids = fields.One2many('of.sale.echeance', 'order_id', string=u"Échéances")

    of_echeances_modified = fields.Boolean(
        u"Les échéances ont besoin d'être recalculées", compute="_compute_of_echeances_modified")
    of_force_invoice_status = fields.Selection([
        ('invoiced', 'Fully Invoiced'),
        ('no', 'Nothing to Invoice')], string=u"Forcer état de facturation",
        help=u"Permet de forcer l'état de facturation de la commande.\n"
             u"Utile pour les commandes facturées qui refusent de changer d'état "
             u"(e.g. une ligne a été supprimée dans la facture).", copy=False
    )
    of_invoice_policy = fields.Selection(
        [('order', u'Quantités commandées'), ('delivery', u'Quantités livrées')], string="Politique de facturation"
    )
    of_fixed_invoice_date = fields.Date(string="Date de facturation fixe")
    of_invoice_date_prev = fields.Date(string=u"Date de facturation prévisonnelle",
                                       compute="_compute_of_invoice_date_prev",
                                       inverse="_inverse_of_invoice_date_prev", store=True)
    of_delivered = fields.Boolean(string=u"Livrée", compute="_compute_delivered", store=True)
    of_allow_quote_addition = fields.Boolean(
        string=u"Permet l'ajout de devis complémentaires", compute='_compute_of_allow_quote_addition')
    of_price_printing = fields.Selection([
        ('order_line', u'Prix par ligne de commande'),
    ], string=u"Impressions des prix", default='order_line', required=True)
    of_apply_on_invoice = fields.Boolean(string=u"Appliquer aux factures", default=True)

    @api.multi
    @api.depends('name', 'date', 'state')
    def name_get(self):
        if not self._context.get('extended_display'):
            return super(SaleOrder, self).name_get()
        result = []
        date_format = '%d/%m/%Y' if self.env.user.lang == 'fr_FR' else DEFAULT_SERVER_DATE_FORMAT
        for record in self:
            date_order = fields.Date.from_string(record.date_order).strftime(date_format)
            order_state = get_selection_label(self, record._name, 'state', record.state)
            record_name = "%s - %s - %s" % (
                record.name, order_state, date_order
            )
            result.append((record.id, record_name))
        return result

    @api.depends('company_id')
    def _compute_of_allow_quote_addition(self):
        option = self.env['ir.values'].get_default('sale.config.settings', 'of_allow_quote_addition')
        for order in self:
            order.of_allow_quote_addition = option

    @api.depends('of_echeance_line_ids', 'amount_total')
    def _compute_of_echeances_modified(self):
        for order in self:
            order.of_echeances_modified = bool(order.of_echeance_line_ids
                                               and float_compare(order.amount_total,
                                                                 sum(order.of_echeance_line_ids.mapped('amount')),
                                                                 precision_rounding=.01))

    @api.depends('order_line', 'order_line.qty_delivered', 'order_line.product_uom_qty')
    def _compute_delivered(self):
        for order in self:
            for line in order.order_line:
                if float_compare(line.qty_delivered, line.product_uom_qty, 2) < 0:
                    order.of_delivered = False
                    break
            else:
                order.of_delivered = True

    @api.depends('of_fixed_invoice_date', 'of_invoice_policy',
                 'order_line', 'order_line.of_invoice_date_prev',
                 'order_line.procurement_ids', 'order_line.procurement_ids.move_ids',
                 'order_line.procurement_ids.move_ids.picking_id.min_date')
    def _compute_of_invoice_date_prev(self):
        for order in self:
            if order.of_fixed_invoice_date or order.of_invoice_policy == 'order':
                order.of_invoice_date_prev = order.of_fixed_invoice_date
            elif order.of_invoice_policy == 'delivery':
                pickings = order.order_line.mapped('procurement_ids')\
                                           .mapped('move_ids')\
                                           .mapped('picking_id')\
                                           .filtered(lambda p: p.state != 'cancel')\
                                           .sorted('min_date')
                if pickings:
                    to_process_pickings = pickings.filtered(lambda p: p.state != 'done')
                    if to_process_pickings:
                        order.of_invoice_date_prev = fields.Date.to_string(
                            fields.Date.from_string(to_process_pickings[0].min_date))
                    else:
                        order.of_invoice_date_prev = fields.Date.to_string(
                            fields.Date.from_string(pickings[-1].min_date))

    def _inverse_of_invoice_date_prev(self):
        for order in self:
            order.of_fixed_invoice_date = order.of_invoice_date_prev

    def _of_get_max_or_min_seq_by_layout(self, what='max'):
        self.ensure_one()
        lines_with_layout = self.order_line.filtered(lambda l: l.layout_category_id)
        seq_by_layout = {}.fromkeys(lines_with_layout.mapped('layout_category_id').ids, 0)
        for layout_id in seq_by_layout:
            if what == 'max':
                seq = max(lines_with_layout.filtered(lambda l: l.layout_category_id.id == layout_id).mapped('sequence'))
            else:
                seq = min(lines_with_layout.filtered(lambda l: l.layout_category_id.id == layout_id).mapped('sequence'))
            seq_by_layout[layout_id] = seq
        return seq_by_layout

    @api.multi
    def of_get_taxes_values(self):
        tax_grouped = {}
        round_curr = self.currency_id.round
        for line in self.order_line:
            price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)

            taxes = line.tax_id.compute_all(price_unit, self.currency_id, line.product_uom_qty,
                                            product=line.product_id, partner=self.partner_shipping_id)['taxes']
            for val in taxes:
                key = val['account_id']

                val['amount'] += val['base'] - round_curr(val['base'])
                if key not in tax_grouped:
                    tax_grouped[key] = {
                        'tax_id': val['id'],
                        'amount': val['amount'],
                        'base': round_curr(val['base'])
                    }
                else:
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base'] += round_curr(val['base'])

        for values in tax_grouped.itervalues():
            values['base'] = round_curr(values['base'])
            values['amount'] = round_curr(values['amount'])
        return tax_grouped

    @api.multi
    def _of_compute_echeances(self):
        self.ensure_one()
        if not self.payment_term_id:
            return False
        dates = {
            'order': self.state not in ('draft', 'sent', 'cancel') and self.confirmation_date,
            'invoice': self.invoice_status == 'invoiced' and self.invoice_ids[0].date_invoice,
            'default': False,
        }
        amounts = self.payment_term_id.compute(self.amount_total, dates=dates)[0]

        amount_total = self.amount_total
        pct_left = 100.0
        pct = 0
        result = [(5, )]
        for term, (date, amount) in itertools.izip(self.payment_term_id.line_ids, amounts):
            pct_left -= pct
            pct = round(100 * amount / amount_total, 2) if amount_total else 0

            line_vals = {
                'name': term.name,
                'percent': pct,
                'amount': amount,
                'date': date,
            }
            result.append((0, 0, line_vals))
        if len(result) > 1:
            result[-1][2]['percent'] = pct_left
        return result

    @api.depends('state', 'order_line.invoice_status', 'of_force_invoice_status')
    def _get_invoiced(self):
        # Appel du super dans tous les cas pour le calcul de invoice_count et invoice_ids
        super(SaleOrder, self)._get_invoiced()
        for order in self:
            if order.of_force_invoice_status:
                order.invoice_status = order.of_force_invoice_status

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        fiscal_position = self.fiscal_position_id
        payment_term = self.payment_term_id

        super(SaleOrder, self).onchange_partner_id()
        self.of_invoice_policy = self.partner_id and self.partner_id.of_invoice_policy or False

        # Si la nouvelle valeur est vide, on remet l'ancienne
        if fiscal_position != self.fiscal_position_id and not self.fiscal_position_id:
            self.fiscal_position_id = fiscal_position.id,
        if payment_term != self.payment_term_id and not self.payment_term_id:
            self.payment_term_id = payment_term.id,

        # Adresses par défaut
        if self.partner_id:
            if not self.partner_invoice_id.of_default_address:
                default_invoice_address = self.partner_id.child_ids.filtered(
                    lambda child: child.type == 'invoice' and child.of_default_address)
                if default_invoice_address:
                    if len(default_invoice_address) > 1:
                        default_invoice_address = default_invoice_address[0]
                    self.partner_invoice_id = default_invoice_address
            if not self.partner_shipping_id.of_default_address:
                default_shipping_address = self.partner_id.child_ids.filtered(
                    lambda child: child.type == 'delivery' and child.of_default_address)
                if default_shipping_address:
                    if len(default_shipping_address) > 1:
                        default_shipping_address = default_shipping_address[0]
                    self.partner_shipping_id = default_shipping_address

    @api.multi
    @api.onchange('partner_shipping_id', 'partner_id')
    def onchange_partner_shipping_id(self):
        fiscal_position = self.fiscal_position_id
        super(SaleOrder, self).onchange_partner_shipping_id()
        # Si la nouvelle valeur est vide, on remet l'ancienne
        if fiscal_position != self.fiscal_position_id and not self.fiscal_position_id:
            self.fiscal_position_id = fiscal_position.id,
        return {}

    @api.onchange('partner_id')
    def onchange_partner_id_warning(self):
        if not self.partner_id:
            return
        partner = self.partner_id

        # If partner has no warning, check its parents
        # invoice_warn is shared between different objects
        if not partner.of_is_sale_warn and partner.parent_id:
            partner = partner.parent_id

        if partner.of_is_sale_warn and partner.invoice_warn != 'no-message':
            return super(SaleOrder, self).onchange_partner_id_warning()
        return

    @api.onchange('payment_term_id')
    def _onchange_payment_term_id(self):
        if self.payment_term_id:
            self.of_echeance_line_ids = self._of_compute_echeances()

    @api.onchange('amount_total')
    def _onchange_amount_total(self):
        self._onchange_payment_term_id()

    @api.multi
    def of_update_dates_echeancier(self):
        for order in self:
            if not order.payment_term_id:
                continue

            dates = {
                'order': order.confirmation_date,
                'invoice': order.invoice_status == 'invoiced' and order.invoice_ids[0].date_invoice,
                'default': False,
            }
            force_dates = [echeance.date for echeance in order.of_echeance_line_ids]
            echeances = order.payment_term_id.compute(order.amount_total, dates=dates, force_dates=force_dates)[0]

            if len(echeances) != len(order.of_echeance_line_ids):
                continue

            for echeance, ech_calc in itertools.izip(order.of_echeance_line_ids, echeances):
                if ech_calc[0] and not echeance.date:
                    echeance.date = ech_calc[0]

    @api.multi
    def action_confirm(self):
        super(SaleOrder, self).action_confirm()
        self.of_update_dates_echeancier()
        return True

    @api.multi
    def of_recompute_echeance_last(self):
        for order in self:
            if not order.of_echeance_line_ids:
                continue

            percent = 100.0
            amount = order.amount_total
            for echeance in order.of_echeance_line_ids:
                if echeance.last:
                    echeance.write({
                        'percent': percent,
                        'amount': amount,
                    })
                else:
                    percent -= echeance.percent
                    amount -= echeance.amount

    @api.multi
    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        # Recalcul de la dernière échéance si besoin
        self.filtered('of_echeances_modified').of_recompute_echeance_last()
        return res

    @api.depends('state', 'order_line', 'order_line.qty_to_invoice', 'order_line.product_uom_qty')
    def _compute_of_to_invoice(self):
        for order in self:
            if order.state not in ('sale', 'done') or order.of_force_invoice_status in ('invoiced', 'no'):
                order.of_to_invoice = False
                continue
            for line in order.order_line:
                if line.qty_to_invoice + line.qty_invoiced < line.product_uom_qty:
                    order.of_to_invoice = False
                    break
            else:
                order.of_to_invoice = True

    @api.depends('margin', 'amount_untaxed')
    def _compute_of_marge(self):
        for order in self:
            cout = order.amount_untaxed - order.margin
            order.of_total_cout = cout
            order.of_marge_pc = 100 * (1 - cout / order.amount_untaxed) if order.amount_untaxed else -100

    def toggle_view(self):
        """ Permet de basculer entre la vue vendeur/client
        """
        self.of_client_view = not self.of_client_view

    @api.multi
    def _of_get_total_lines_by_group(self):
        """
        Retourne les lignes de la commande, séparées en fonction du groupe dans lequel les afficher.
        Les groupes sont ceux définis par l'objet of.invoice.report.total, permettant de déplacer le rendu des
          lignes de commande sous le total hors taxe ou TTC.
        Les groupes sont affichés dans leur ordre propre, puis les lignes dans l'ordre d'apparition dans la commande.
        @param return: Liste de couples (groupe, lignes de commande). Le 1er élément vaut (False, Lignes non groupées).
        """
        self.ensure_one()
        group_obj = self.env['of.invoice.report.total.group']

        lines = self.order_line
        products = lines.mapped('product_id')
        product_ids = list(products._ids)
        categ_ids = list(products.mapped('categ_id')._ids)
        groups = group_obj.search([('order', '=', True),
                                   '|', ('id', '=', group_obj.get_group_paiements().id),
                                   '|', ('product_ids', 'in', product_ids), ('categ_ids', 'in', categ_ids)])

        result = []
        for group in groups:
            if group.is_group_paiements():
                group_paiement_lines = group.filter_lines(lines)
                if group_paiement_lines is not False:
                    lines -= group_paiement_lines
                break
        for group in groups:
            if group.is_group_paiements():
                result.append((group, group_paiement_lines))
            else:
                group_lines = group.filter_lines(lines)
                if group_lines is not False:
                    # On ajoute cette vérification pour ne pas afficher des lignes à 0 dans les paiements et
                    # ne pas afficher le groupe si toutes les lignes sont à 0.
                    group_lines_2 = group_lines.filtered(lambda l: l.price_subtotal)
                    if group_lines_2:
                        result.append((group, group_lines_2))
                    # On enlève quand même toutes les lignes du groupe pour ne pas qu'elle s'affichent
                    lines -= group_lines
        if lines:
            result = [(False, lines)] + result
        else:
            result = [(False, self.order_line.mapped('invoice_lines'))]
            # On ajoute quand-même les paiements
            for group in groups:
                if group.is_group_paiements():
                    result.append((group, lines))  # lines est vide
        return result

    @api.multi
    def _of_get_printable_lines(self):
        """ [IMPRESSION]
        Renvoie les lignes à afficher
        """
        return self._of_get_total_lines_by_group()[0][1]

    def _prepare_tax_line_vals(self, line, tax):
        """ Emulation de la fonction du même nom du modèle 'account.invoice'
            Permet de récupérer la clé de groupement dans _of_get_printable_totals
        """
        vals = {
            'name': tax['name'],
            'tax_id': tax['id'],
            'amount': tax['amount'],
            'base': tax['base'],
            'manual': False,
            'sequence': tax['sequence'],
            'account_analytic_id': tax['analytic'] or False,
            'account_id': tax['account_id'] or tax['refund_account_id'] or False,

        }
        return vals

    @api.multi
    def _of_get_printable_totals(self):
        """ [IMPRESSION]
        Retourne un dictionnaire contenant les valeurs à afficher dans les totaux de la commande pdf.
        Dictionnaire de la forme :
        {
            'subtotal' : Total HT des lignes affichées,
            'untaxed' : [[('libellé', montant),...], ('libellé total': montant_total)]
            'taxes' : idem,
            'total' : idem,
        }
        Les listes untaxed, taxes et total pourraient être regroupés en une seule.
        Ce format pourra aider aux héritages (?).
        """
        self.ensure_one()
        tax_obj = self.env['account.tax']
        round_curr = self.currency_id.round

        group_lines = self._of_get_total_lines_by_group()

        result = {}
        result['subtotal'] = sum(group_lines[0][1].mapped('price_subtotal'))
        total_amount = result['subtotal']

        i = 1
        untaxed_lines = group_lines[0][1]
        # --- Sous-totaux hors taxes ---
        result_untaxed = []
        while i < len(group_lines) and group_lines[i][0].position == '0-ht':
            group, lines = group_lines[i]
            i += 1
            untaxed_lines |= lines
            lines_vals = []
            for line in lines:
                lines_vals.append((line.of_get_line_name()[0], line.price_subtotal))
                total_amount += line.price_subtotal
            total_vals = (group.subtotal_name, round_curr(total_amount))
            result_untaxed.append([lines_vals, total_vals])
        result['untaxed'] = result_untaxed

        # --- Ajout des taxes ---
        # Code copié depuis account.invoice.get_taxes_values()
        tax_grouped = {}
        for line in untaxed_lines:
            price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(price_unit, self.currency_id, line.product_uom_qty, line.product_id,
                                            self.partner_id)['taxes']
            for tax_val in taxes:
                val = self._prepare_tax_line_vals(line, tax_val)
                tax = tax_obj.browse(tax_val['id'])
                key = tax.get_grouping_key(val)

                val['amount'] += val['base'] - round_curr(val['base'])
                if key not in tax_grouped:
                    tax_grouped[key] = val
                    tax_grouped[key]['name'] = tax.description or tax.name
                    tax_grouped[key]['group'] = tax.tax_group_id
                else:
                    tax_grouped[key]['amount'] += val['amount']
        # Taxes groupées par groupe de taxes (cf account.invoice._get_tax_amount_by_group())
        tax_vals_dict = {}
        for tax in sorted(tax_grouped.values(), key=lambda t: t['name']):
            amount = round_curr(tax['amount'])
            tax_vals_dict.setdefault(tax['group'], [tax['group'].name, 0])
            tax_vals_dict[tax['group']][1] += amount
            total_amount += amount
        result['taxes'] = [[tax_vals_dict.values(), (_("Total TTC"), round_curr(total_amount))]]

        # --- Sous-totaux TTC ---
        result_total = []
        while i < len(group_lines):
            # Tri des paiements par date
            group, lines = group_lines[i]
            i += 1
            if group.is_group_paiements():
                lines_vals = self._of_get_printable_payments(lines)
                if not lines_vals:
                    continue
                for line in lines_vals:
                    total_amount -= line[1]
            else:
                lines_vals = []
                for line in lines:
                    lines_vals.append((line.of_get_line_name()[0], line.price_total))
                    total_amount += line.price_total
            total_vals = (group.subtotal_name, round_curr(total_amount))
            result_total.append([lines_vals, total_vals])
        result['total'] = result_total

        return result

    @api.multi
    def order_lines_layouted(self):
        """
        Retire les lignes de commande qui doivent êtres affichées dans les totaux.
        """
        report_pages_full = super(SaleOrder, self).order_lines_layouted()
        report_lines = self._of_get_printable_lines()
        report_pages = []
        for page_full in report_pages_full:
            page = []
            for group in page_full:
                lines = [line for line in group['lines'] if line in report_lines]
                if lines:
                    group['lines'] = lines
                    page.append(group)
            if page:
                report_pages.append(page)
        return report_pages

    @api.multi
    def _of_get_printable_payments(self, order_lines):
        """ [IMPRESSION]
        Renvoie les lignes à afficher.
        Permet l'affichage des paiements dans une commande.
        On ne va pas chercher les paiements affectés à la commande car le lien est ajouté dans of_sale_payment
        """
        invoice_obj = self.env['account.invoice']
        account_move_line_obj = self.env['account.move.line']
        # Liste des factures et factures d'acompte
        invoices = self.mapped('order_line').mapped('invoice_lines').mapped('invoice_id')

        # Retour de tous les paiements des factures
        # On distingue les paiements de la facture principale de ceux des factures liées
        result = []
        for invoice in invoices:
            widget = json.loads(invoice.payments_widget.replace("'", "\'"))
            if not widget:
                continue
            for payment in widget.get('content', []):
                # Les paiements sont classés dans l'ordre chronologique
                move_line = account_move_line_obj.browse(payment['payment_id'])
                name = invoice_obj._of_get_payment_display(move_line)
                result.append((name, payment['amount']))
        return result

    @api.multi
    def _prepare_invoice(self):
        """ Rajout date visite technique. Attention en cas de facturation de plusieurs bons de commande à la fois"""
        self.ensure_one()
        if self.company_id:
            self = self.with_context(company_id=self.company_id.id)
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals["of_date_vt"] = self.of_date_vt
        if self.of_apply_on_invoice:
            invoice_vals["of_price_printing"] = self.of_price_printing
        return invoice_vals

    @api.multi
    def copy(self, default=None):
        res = super(SaleOrder, self).copy(default=default)
        res._onchange_payment_term_id()
        return res

    @api.multi
    def action_invoice_create(self, grouped=False, final=False):
        grouped = self.env['ir.values'].get_default('sale.config.settings', 'of_invoice_grouped')
        invoice_ids = super(SaleOrder, self).action_invoice_create(grouped=grouped, final=final)
        invoices = self.env['account.invoice'].browse(invoice_ids)

        if self._context.get('of_include_null_qty_lines', False) and invoices:
            for order in self:
                # On récupère la facture générée correspondant à cette commande
                invoice = invoices.filtered(lambda inv: inv.origin == order.name)
                if invoice:
                    # On ajoute dans la facture les lignes correspondantes aux lignes de commande en quantité 0
                    # et qui n'ont pas de lignes de facture associées
                    for order_line in order.order_line.filtered(
                            lambda l: l.product_uom_qty == 0.0 and not l.invoice_lines):
                        vals = order_line._prepare_invoice_line(qty=0.0)
                        vals.update({'invoice_id': invoice.id, 'sale_line_ids': [(6, 0, [order_line.id])]})
                        self.env['account.invoice.line'].create(vals)

        # Pour les factures groupées, on indique pour chaque ligne de facture sa commande d'origine
        for inv in invoices:
            if len(inv.invoice_line_ids.mapped('sale_line_ids').mapped('order_id')) > 1:
                for line in inv.invoice_line_ids:
                    order_line = line.sale_line_ids[:1]
                    line.name = "%s %s\n%s" % (
                        order_line.order_id.name, order_line.order_id.client_order_ref or "", line.name)

        return invoice_ids

    @api.multi
    def action_add_quote(self):
        self.ensure_one()

        if self.state != 'sale':
            raise UserError(u"Vous ne pouvez pas ajouter un devis complémentaire à une commande non validée.")

        wizard = self.env['of.sale.order.add.quote.wizard'].create({
            'order_id': self.id,
        })

        return {
            'type': 'ir.actions.act_window',
            'name': "Ajouter un devis complémentaire",
            'view_mode': 'form',
            'res_model': 'of.sale.order.add.quote.wizard',
            'res_id': wizard.id,
            'target': 'new',
        }

    @api.multi
    def of_get_taxes_display(self):
        tax_obj = self.env['account.tax']
        tax_grouped = []
        round_curr = self.currency_id.round
        for line in self.order_line:
            price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)

            taxes = line.tax_id.compute_all(price_unit, self.currency_id, line.product_uom_qty,
                                            product=line.product_id, partner=self.partner_shipping_id)['taxes']
            for val in taxes:
                key = val['id']
                tax = tax_obj.browse(key)
                for values in tax_grouped:
                    if values['id'] == key:
                        values['amount'] += val['amount']
                        values['base'] += round_curr(val['base'])
                        break
                else:
                    tax_grouped.append({
                        'id': key,
                        'name': tax.description,
                        'amount': val['amount'],
                        'base': round_curr(val['base'])
                    })
        for values in tax_grouped:
            values['base'] = round_curr(values['base'])
            values['amount'] = round_curr(values['amount'])
        return tax_grouped


class SaleOrderLine(models.Model):
    _name = 'sale.order.line'
    _inherit = ['sale.order.line', 'of.readgroup']

    price_unit = fields.Float(digits=False, help="""
    Prix unitaire de l'article.
    À entrer HT ou TTC suivant la TVA de la ligne de commande.
    """)
    of_client_view = fields.Boolean(string="Vue client/vendeur", related="order_id.of_client_view")
    of_article_principal = fields.Boolean(
        string="Article principal", help="Cet article est l'article principal de la commande"
    )
    of_product_categ_id = fields.Many2one(
        'product.category', related='product_id.categ_id', string=u"Catégorie d'article", store=True, index=True)
    date_order = fields.Datetime(related='order_id.date_order', string="Date de commande", store=True, index=True)
    confirmation_date_order = fields.Datetime(
        related='order_id.confirmation_date', string="Date de confirmation de commande", store=True, index=True)
    of_gb_partner_tag_id = fields.Many2one(
        'res.partner.category', compute=lambda *a, **k: {}, search='_search_of_gb_partner_tag_id',
        string="Étiquette client", of_custom_groupby=True
    )
    of_price_unit_display = fields.Float(related='product_id.list_price', string=u"Prix unitaire", readonly=True)
    of_product_forbidden_discount = fields.Boolean(string=u"Remise interdite pour cet article")

    of_price_unit_ht = fields.Float(
        string='Unit Price excl', compute='_compute_of_price_unit', help="Unit price without taxes", store=True
    )
    of_price_unit_ttc = fields.Float(
        string='Unit Price incl', compute='_compute_of_price_unit', help="Unit price with taxes", store=True
    )
    of_marge_pc = fields.Float(
        compute='_compute_of_marge', string=u"Marge %", store=True)

    of_product_default_code = fields.Char(related='product_id.default_code', string=u"Référence article", readonly=True)
    of_order_line_option_id = fields.Many2one(comodel_name='of.order.line.option', string=u"Option")
    of_reset_option = fields.Boolean(string=u"Réinitialiser l'option ?")

    of_confirmation_date = fields.Datetime(
        string="Date de confirmation", related="order_id.confirmation_date", store=True)
    of_invoice_policy = fields.Selection([('order', u'Quantités commandées'), ('delivery', u'Quantités livrées')],
                                         string="Politique de facturation",
                                         compute="_compute_of_invoice_policy",
                                         store=True)
    of_invoice_date_prev = fields.Date(string=u"Date de facturation prévisionnelle",
                                       compute="_compute_of_invoice_date_prev",
                                       store=True)
    of_seller_price = fields.Float(string=u"Prix d'achat")

    of_date_tarif = fields.Date(string="Date du tarif", related="product_id.date_tarif", readonly=True)
    of_obsolete = fields.Boolean(string=u"Article obsolète", related="product_id.of_obsolete", readonly=True)
    of_product_image_ids = fields.Many2many('of.product.image', string='Images')
    of_product_attachment_ids = fields.Many2many("ir.attachment", string="Documents joints")
    # Champ servant au calcul du domain de of_product_attachment_ids
    of_product_attachment_computed_ids = fields.Many2many(
        "ir.attachment", string="Documents joints",
        compute='_compute_of_product_attachment_computed_ids')
    # A supprimer après la prochaine màj
    of_product_attachment_computed = fields.Boolean(compute=lambda s: None)

    @api.model_cr_context
    def _auto_init(self):
        """
        Modification du nom du champ 'of_product_seller_price' en 'of_seller_price' dans les vues xml.
        TODO: A SUPPRIMER APRES INSTALLATION !
        """
        cr = self._cr
        cr.execute(
            "SELECT 1 FROM information_schema.columns WHERE table_name = %s AND column_name = 'of_seller_price'",
            (self._table,))
        exists = bool(cr.fetchall())
        res = super(SaleOrderLine, self)._auto_init()
        if not exists:
            cr.execute(
                """ UPDATE  ir_ui_view
                    SET     arch_db     = REPLACE(arch_db, 'of_product_seller_price', 'of_seller_price')
                    WHERE   arch_db     LIKE '%of_product_seller_price%'
                """)
        return res

    of_price_management_variation = fields.Float(
        string=u"Montant unitaire de la variation de prix liée à la gestion de prix")
    of_unit_price_variation = fields.Float(string=u"Montant unitaire de la variation de prix")

    @api.depends('price_subtotal', 'margin')
    def _compute_of_marge(self):
        for line in self:
            if line.price_subtotal:
                line.of_marge_pc = line.margin * 100.0 / line.price_subtotal
            else:
                line.of_marge_pc = 0.0

    @api.depends('product_id')
    def _compute_of_product_attachment_computed_ids(self):
        product_obj = self.env['product.product']
        attachment_obj = self.env['ir.attachment']
        for line in self:
            # On récupère toutes les variantes du modèle d'article
            product_ids = product_obj.search([('product_tmpl_id', '=', line.product_id.product_tmpl_id.id)])

            # On récupère toutes les PJ pdf du modèle d'article et de ses variantes
            domain = [
                '&',
                '|',
                '&',
                ('res_model', '=', 'product.template'),
                ('res_id', '=', line.product_id.product_tmpl_id.id),
                '&',
                ('res_model', '=', 'product.product'),
                ('res_id', 'in', product_ids.ids),
                ('mimetype', '=', 'application/pdf')
            ]
            attachment_ids = attachment_obj.search(domain)
            line.of_product_attachment_computed_ids = attachment_ids

    @api.depends('price_unit', 'order_id.currency_id', 'order_id.partner_shipping_id', 'product_id',
                 'price_subtotal', 'product_uom_qty')
    def _compute_of_price_unit(self):
        """
        @ TODO: à fusionner avec _compute_amount
        :return:
        """
        for line in self:
            taxes = line.tax_id.compute_all(line.price_unit, line.order_id.currency_id, 1,
                                            product=line.product_id, partner=line.order_id.partner_shipping_id)
            line.of_price_unit_ht = taxes['total_excluded']
            line.of_price_unit_ttc = taxes['total_included']

    @api.depends('product_id', 'product_id.invoice_policy',
                 'order_id', 'order_id.of_invoice_policy',
                 'order_partner_id', 'order_partner_id.of_invoice_policy')
    def _compute_of_invoice_policy(self):
        for line in self:
            line.of_invoice_policy = line.order_id.of_invoice_policy \
                or line.order_partner_id.of_invoice_policy or line.product_id.invoice_policy \
                or self.env['ir.values'].get_default('product_template', 'invoice_policy')

    @api.depends('of_invoice_policy',
                 'order_id', 'order_id.of_fixed_invoice_date',
                 'procurement_ids', 'procurement_ids.move_ids', 'procurement_ids.move_ids')
    def _compute_of_invoice_date_prev(self):
        for line in self:
            if line.of_invoice_policy == 'order':
                line.of_invoice_date_prev = line.order_id.of_invoice_date_prev
            elif line.of_invoice_policy == 'delivery':
                moves = line.procurement_ids.mapped('move_ids').sorted('date_expected')
                if moves:
                    line.of_invoice_date_prev = fields.Date.to_string(fields.Date.from_string(moves[0].date_expected))

    @api.model
    def _search_of_gb_partner_tag_id(self, operator, value):
        return [('order_partner_id.category_id', operator, value)]

    @api.model
    def _read_group_process_groupby(self, gb, query):
        # Ajout de la possibilité de regrouper par employé
        if gb != 'of_gb_partner_tag_id':
            return super(SaleOrderLine, self)._read_group_process_groupby(gb, query)

        alias, _ = query.add_join(
            (self._table, 'res_partner_res_partner_category_rel', 'order_partner_id', 'partner_id', 'partner_category'),
            implicit=False, outer=True,
        )

        return {
            'field': gb,
            'groupby': gb,
            'type': 'many2one',
            'display_format': None,
            'interval': None,
            'tz_convert': False,
            'qualified_field': '"%s".category_id' % (alias,)
        }

    @api.model
    def of_custom_groupby_generate_order(self, alias, order_field, query, reverse_direction, seen):
        if order_field == 'of_gb_partner_tag_id':
            dest_model = self.env['res.partner.category']
            m2o_order = dest_model._order
            if not regex_order.match(m2o_order):
                # _order is complex, can't use it here, so we default to _rec_name
                m2o_order = dest_model._rec_name

            rel_alias, _ = query.add_join(
                (alias, 'res_partner_res_partner_category_rel',
                 'order_partner_id', 'partner_id', 'partner_category_rel'),
                implicit=False, outer=True)
            dest_alias, _ = query.add_join(
                (rel_alias, 'res_partner_category', 'category_id', 'id', 'partner_category'),
                implicit=False, outer=True)
            return dest_model._generate_order_by_inner(dest_alias, m2o_order, query,
                                                       reverse_direction, seen)
        return []

    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        res = super(SaleOrderLine, self).product_id_change()
        afficher_descr_fab = self.env.user.company_id.afficher_descr_fab
        afficher = afficher_descr_fab == 'devis' or afficher_descr_fab == 'devis_factures'
        product = self.product_id.with_context(
            lang=self.order_id.partner_id.lang,
            partner=self.order_id.partner_id.id,
        )
        if product and product.description_fabricant and afficher:
            name = self.name
            name += '\n' + product.description_fabricant
            self.update({'name': name})

        # Remise interdite

        if self.product_id:
            self.of_product_forbidden_discount = self.product_id.of_forbidden_discount
            if self.product_id.of_forbidden_discount and self.of_discount_formula:
                self.of_discount_formula = False
            if self.product_id.categ_id:
                self.of_article_principal = self.product_id.categ_id.of_article_principal
            if self.env.user.has_group('sale.group_sale_layout'):
                if self.product_id.categ_id.of_layout_id:
                    self.layout_category_id = self.product_id.categ_id.of_layout_id
            if self.env.user.has_group('of_sale.group_of_sale_multiimage'):
                if self.product_id.product_tmpl_id.of_product_image_ids:
                    of_product_image_ids = self.product_id.product_tmpl_id.of_product_image_ids
                    self.of_product_image_ids = self.product_id.product_tmpl_id.of_product_image_ids
                    res['domain']['of_product_image_ids'] = [('id', 'in', of_product_image_ids.ids)]
            if self.env.user.has_group('of_sale.group_of_sale_print_attachment'):
                attachment_ids = self.env['ir.attachment'].search(
                    [('id', 'in', self.of_product_attachment_computed_ids.ids)])
                self.of_product_attachment_ids = attachment_ids

        return res

    @api.onchange('product_id', 'product_uom')
    def product_id_change_margin(self):
        super(SaleOrderLine, self).product_id_change_margin()

        if not self.order_id.pricelist_id or not self.product_id or not self.product_uom:
            return

        frm_cur = self.env.user.company_id.currency_id
        to_cur = self.order_id.pricelist_id.currency_id
        seller_price = self.product_id.of_seller_price
        if self.product_uom != self.product_id.uom_id:
            seller_price = self.product_id.uom_id._compute_price(seller_price, self.product_uom)
        ctx = self.env.context.copy()
        ctx['date'] = self.order_id.date_order
        self.of_seller_price = frm_cur.with_context(ctx).compute(seller_price, to_cur, round=False)

    @api.onchange('of_order_line_option_id')
    def _onchange_of_order_line_option_id(self):
        if self.of_order_line_option_id and self.product_id:
            option = self.of_order_line_option_id
            if option.sale_price_update and self.price_unit:
                if option.sale_price_update_type == 'fixed':
                    self.price_unit = self.price_unit + option.sale_price_update_value
                elif option.sale_price_update_type == 'percent':
                    self.price_unit = self.price_unit + self.price_unit * (option.sale_price_update_value / 100)
                self.price_unit = self.order_id.currency_id.round(self.price_unit)
            if option.purchase_price_update and self.purchase_price:
                if option.purchase_price_update_type == 'fixed':
                    self.purchase_price = self.purchase_price + option.purchase_price_update_value
                elif option.purchase_price_update_type == 'percent':
                    self.purchase_price = \
                        self.purchase_price + self.purchase_price * (option.purchase_price_update_value / 100)
                self.purchase_price = self.order_id.currency_id.round(self.purchase_price)
            if option.description_update:
                self.name = self.name + "\n%s" % option.description_update

    @api.onchange('of_reset_option')
    def _onchange_of_reset_option(self):
        if self.of_reset_option:
            product = self.product_id.with_context(
                lang=self.order_id.partner_id.lang,
                partner=self.order_id.partner_id.id,
                quantity=self.product_uom_qty,
                date=self.order_id.date_order,
                pricelist=self.order_id.pricelist_id.id,
                uom=self.product_uom.id
            )

            if self.order_id.pricelist_id and self.order_id.partner_id:
                self.price_unit = self.env['account.tax']._fix_tax_included_price_company(
                    self._get_display_price(product), product.taxes_id, self.tax_id, self.company_id)
            self.purchase_price = product.standard_price
            if self.of_order_line_option_id.description_update:
                self.name = self.name.replace(self.of_order_line_option_id.description_update, '')
            self.of_order_line_option_id = False
            self.of_reset_option = False

    @api.onchange('of_product_forbidden_discount')
    def _onchange_of_product_forbidden_discount(self):
        if self.of_product_forbidden_discount and self.product_id:
            self.price_unit = self.product_id.list_price

    def of_get_line_name(self):
        self.ensure_one()
        # inhiber l'affichage de la référence
        afficher_ref = self.env['ir.values'].get_default('sale.config.settings', 'pdf_display_product_ref_setting')
        le_self = self.with_context(
            lang=self.order_id.partner_id.lang,
            partner=self.order_id.partner_id.id,
        )
        name = le_self.name
        if not afficher_ref:
            if name.startswith("["):
                splitted = name.split("]")
                if len(splitted) > 1:
                    splitted.pop(0)
                    name = ']'.join(splitted).strip()
        return name.split("\n")  # utilisation t-foreach dans template qweb

    def _write(self, vals):
        for field in vals:
            if field != 'of_product_categ_id':
                break
        else:
            self = self.sudo()

        if 'price_reduce' in vals and len(self) == 1:
            vals['of_unit_price_variation'] = \
                self.of_price_management_variation + vals.get('price_reduce', 0) - self.price_unit

        return super(SaleOrderLine, self)._write(vals)

    @api.multi
    def unlink(self):
        """
        Ne pas autoriser la suppression de ligne de commandes si la ligne est déjà présente sur une facture qui n'est
        pas une facture annulée n'ayant jamais été validée.
        """
        locked_invoice_lines = self.mapped('invoice_lines').filtered(
            lambda l: l.invoice_id.state != 'cancel' or l.invoice_id.move_name)
        if locked_invoice_lines:
            raise UserError(u"""Vous ne pouvez supprimer une ligne d'article liée à une facture.\n"""
                            u"""Veuillez annuler vos modifications.""")
        return super(SaleOrderLine, self).unlink()

    @api.model
    def create(self, vals):
        """
        Au moment de la sauvegarde de la commande, les images articles ne sont pas toujours sauvegardées
        car renseignées par un onchange et affichage en vue en kanban, du coup on surcharge le create
        """
        if vals.get('layout_category_id') and 'sequence' not in vals:
            order = self.env['sale.order'].browse(vals['order_id'])
            max_sequence = order._of_get_max_or_min_seq_by_layout().get(vals['layout_category_id'], 0)
            vals['sequence'] = max_sequence + 1
        res = super(SaleOrderLine, self).create(vals)
        if 'of_product_image_ids' in vals.keys() and vals['of_product_image_ids'] and not res.of_product_image_ids:
            res.with_context(already_tried=True).of_product_image_ids = vals['of_product_image_ids']
        return res

    @api.multi
    def write(self, vals):
        """
        Si un des champ de blocked est présent ET une ligne modifiée ne doit pas avoir de modification alors renvoi une
        erreur. Le champ of_discount_formula est dans le module of_sale_discount, la façon dont on vérifie la présence
        des champs dans vals ne provoque pas d'erreur si le module n'est pas installé.
        TODO: Permettre de modifier le montant si modification viens de la facture d'acompte
        """
        force = self._context.get('force_price')
        blocked = [x for x in ('price_unit', 'product_uom_qty', 'product_uom', 'discount', 'of_discount_formula')
                   if x in vals.keys()]
        for line in self:
            locked_invoice_lines = line.mapped('invoice_lines').filtered(lambda l: l.of_is_locked)
            if locked_invoice_lines and blocked and not force:
                raise UserError(u"""Cette ligne ne peut être modifiée : %s""" % line.name)

        # Au moment de la sauvegarde de la commande, les images articles ne sont pas toujours sauvegardées, car
        # renseignées par un onchange et affichage en vue en kanban. Du coup, on surcharge le write
        if 'already_tried' not in self._context:
            if 'of_product_image_ids' in vals.keys() and vals['of_product_image_ids'] and not self.of_product_image_ids:
                self.with_context(already_tried=True).of_product_image_ids = vals['of_product_image_ids']

        if vals.get('layout_category_id') and 'sequence' not in vals:
            new_layout = self.env['sale.layout_category'].browse(vals['layout_category_id'])
            for line in self:
                old_layout = line.layout_category_id
                order = line.order_id
                if old_layout.sequence < new_layout.sequence:
                    sequence = order._of_get_max_or_min_seq_by_layout('min').get(vals['layout_category_id'], 0)
                    vals['sequence'] = sequence - 1
                else:
                    sequence = order._of_get_max_or_min_seq_by_layout().get(vals['layout_category_id'], 0)
                    vals['sequence'] = sequence + 1

        return super(SaleOrderLine, self).write(vals)

    @api.multi
    def _additionnal_tax_verifications(self):
        invoice_line_obj = self.env['account.invoice.line']
        if self.product_id and self.product_id.id in invoice_line_obj.get_locked_product_ids():
            return True
        if self.product_id and self.product_id.categ_id and self.product_id.categ_id.id in invoice_line_obj.\
                get_locked_category_ids():
            return True
        return False

    @api.multi
    def _compute_tax_id(self):
        return super(SaleOrderLine, self.filtered(lambda line: not line._additionnal_tax_verifications())).\
            _compute_tax_id()

    @api.depends('state', 'product_uom_qty', 'qty_delivered', 'qty_to_invoice', 'qty_invoiced',
                 'order_id.of_invoice_policy', 'order_id.partner_id.of_invoice_policy')
    def _compute_invoice_status(self):
        """
        Compute the invoice status of a SO line. Possible statuses:
        - no: if the SO is not in status 'sale' or 'done', we consider that there is nothing to
          invoice. This is also hte default value if the conditions of no other status is met.
        - to invoice: we refer to the quantity to invoice of the line. Refer to method
          `_get_to_invoice_qty()` for more information on how this quantity is calculated.
        - upselling: this is possible only for a product invoiced on ordered quantities for which
          we delivered more than expected. The could arise if, for example, a project took more
          time than expected but we decided not to invoice the extra cost to the client. This
          occurs only in state 'sale', so that when a SO is set to done, the upselling opportunity
          is removed from the list.
        - invoiced: the quantity invoiced is larger or equal to the quantity ordered.
        """
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for line in self:
            invoice_policy = line.of_invoice_policy
            if line.state not in ('sale', 'done'):
                line.invoice_status = 'no'
            elif not float_is_zero(line.qty_to_invoice, precision_digits=precision):
                line.invoice_status = 'to invoice'
            elif line.state == 'sale' and invoice_policy == 'order' and \
                    float_compare(line.qty_delivered, line.product_uom_qty, precision_digits=precision) == 1:
                line.invoice_status = 'upselling'
            elif float_compare(line.qty_invoiced, line.product_uom_qty, precision_digits=precision) >= 0:
                line.invoice_status = 'invoiced'
            else:
                line.invoice_status = 'no'

    @api.depends('qty_invoiced', 'qty_delivered', 'product_uom_qty', 'order_id.state',
                 'order_id.of_invoice_policy', 'order_id.partner_id.of_invoice_policy')
    def _get_to_invoice_qty(self):
        """
        Compute the quantity to invoice. If the invoice policy is order, the quantity to invoice is
        calculated from the ordered quantity. Otherwise, the quantity delivered is used.
        """
        for line in self:
            invoice_policy = line.of_invoice_policy
            if line.order_id.state in ['sale', 'done']:
                if invoice_policy == 'order':
                    line.qty_to_invoice = line.product_uom_qty - line.qty_invoiced
                elif invoice_policy == 'delivery':
                    line.qty_to_invoice = line.qty_delivered - line.qty_invoiced
            else:
                line.qty_to_invoice = 0

    def of_get_price_unit(self):
        """Renvoi le prix unitaire type."""
        self.ensure_one()
        product = self.product_id.with_context(
            lang=self.order_id.partner_id.lang,
            partner=self.order_id.partner_id.id,
            quantity=self.product_uom_qty,
            date=self.order_id.date_order,
            pricelist=self.order_id.pricelist_id.id,
            uom=self.product_uom.id,
            fiscal_position=self.env.context.get('fiscal_position')
        )
        return self.env['account.tax']._fix_tax_included_price_company(
            self._get_display_price(product), product.taxes_id, self.tax_id, self.company_id)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if 'of_marge_pc' in fields and 'margin' not in fields:
            fields.append('margin')
        if 'of_marge_pc' in fields and 'price_subtotal' not in fields:
            fields.append('price_subtotal')
        res = super(SaleOrderLine, self).read_group(
            domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        for line in res:
            if 'of_marge_pc' in fields:
                if 'margin' in line and line['margin'] is not None and \
                        'price_subtotal' in line and line['price_subtotal']:
                    line['of_marge_pc'] = round(100.0 * line['margin'] / line['price_subtotal'], 2)
                else:
                    line['of_marge_pc'] = 0.0
        return res


class SaleLayoutCategory(models.Model):
    _inherit = 'sale.layout_category'

    active = fields.Boolean(string="Active", default=True)


class OFOrderLineOption(models.Model):
    _name = 'of.order.line.option'
    _description = u"Option pour les lignes de commande (Achat et Vente)"

    name = fields.Char(string=u"Nom", required=True)
    purchase_price_update = fields.Boolean(string=u"Modification du prix d'achat")
    purchase_price_update_type = fields.Selection(
        selection=[('fixed', u"Montant fixe"),
                   ('percent', u"Pourcentage")], string=u"Type de modification du prix d'achat")
    purchase_price_update_value = fields.Float(string=u"Valeur de modification du prix d'achat")
    sale_price_update = fields.Boolean(string=u"Modification du prix de vente")
    sale_price_update_type = fields.Selection(
        selection=[('fixed', u"Montant fixe"),
                   ('percent', u"Pourcentage")], string=u"Type de modification du prix de vente")
    sale_price_update_value = fields.Float(string=u"Valeur de modification du prix de vente")
    description_update = fields.Text(string=u"Description de la ligne de commande")
