# -*- coding: utf-8 -*-

from odoo import api, fields, models
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError

# Fonction toute faite pour le formatage de valeur monétaire
from odoo.addons.mail.models.mail_template import format_amount

# Dans le cadre de la remise globale, on autorise l'utilisateur à choisir le total TTC de sa commande.
# Afin de permettre ce tour de force (tous les montants TTC ne sont pas atteignables), on augmente la précision du
#  prix de vente stocké en base de données.
# Odoo conserve l'arrondi défini dans l'objet 'decimal.precision' pour l'affichage, mais utilise la pleine précision
#  pour les calculs des montants TTC


class GestionPrix(models.TransientModel):
    u"""
    Ce wizard permet l'application d'une remise globale sur les articles, ainsi que le choix d'un prix TTC.
    Il permet également de remettre les articles au prix de vente standard
    Il permet également la visualisation de la marge commerciale ligne par ligne

    """
    _name = 'of.sale.order.gestion.prix'
    _description = "Gestion des prix"

    def _get_selection_mode_calcul(self):
        u"""Renvoie les possibilités de mode de calcul en fonction du droit d'afficher les marges."""
        liste = [
            ('prix_ttc_cible', 'montant total TTC cible'),
            ('montant_ttc', u'montant TTC à déduire'),
            ('prix_ht_cible', 'montant total HT cible'),
            ('montant_ht', u'montant HT à déduire'),
            ('pc', u'% de remise sur les lignes sélectionnées'),
        ]
        if self.user_has_groups('of_sale.of_group_sale_marge_manager'):
            liste.append(('pc_marge', '% marge'))
        liste.append(('reset', 'remettre au prix magasin'))  # Avec application de la liste de prix du client
        return liste

    order_id = fields.Many2one('sale.order', string='Devis/commande', required=True, ondelete='cascade')
    methode_remise = fields.Selection(
        selection=_get_selection_mode_calcul, default='prix_ttc_cible', string=u"Mode de calcul",
        help=u"Détermine comment est calculée la remise sur les lignes sélectionnées du devis"
    )
    line_ids = fields.One2many('of.sale.order.gestion.prix.line', 'wizard_id', string=u'Lignes impactées')
    valeur = fields.Float(string='Valeur', digits=dp.get_precision('Sale Price'))

    marge_initiale = fields.Monetary(string='marge initiale', related='order_id.margin', related_sudo=False)
    pc_marge_initiale = fields.Float(string='% marge initiale', related='order_id.of_marge_pc', related_sudo=False)
    montant_total_ttc_initial = fields.Monetary(
        string='Total TTC initial', related='order_id.amount_total', readonly=True
    )
    montant_total_ht_initial = fields.Monetary(
        string='Total HT initial', related='order_id.amount_untaxed', readonly=True
    )

    currency_id = fields.Many2one(related='order_id.currency_id')
    marge_simul = fields.Monetary(
        string=u'marge simulée', digits=dp.get_precision('Sale Price'), compute='_compute_montant_simul'
    )
    pc_marge_simul = fields.Float(
        string=u'% marge simulée', digits=dp.get_precision('Sale Price'), compute='_compute_montant_simul'
    )
    montant_total_ttc_simul = fields.Monetary(
        string=u'Total TTC simulé', digits=dp.get_precision('Sale Price'), compute='_compute_montant_simul')
    montant_total_ht_simul = fields.Monetary(
        string=u'Total HT simulé', digits=dp.get_precision('Sale Price'), compute='_compute_montant_simul')
    afficher_remise = fields.Boolean(
        string='Afficher dans notes',
        help=u"Affiche le montant de la remise effectuée dans les notes du devis/de la commande.")

    arrondi_mode = fields.Selection(
        [
            ('no', "Pas d'arrondi"),
            ('total_excluded', "Arrondi sur le montant HT"),
            ('total_included', "Arrondi sur le montant TTC"),
        ], string="Arrondi par ligne", required=True, default='no')

    arrondi_prec = fields.Selection(
        [
            ('-1', u"Arrondir aux 10 € les plus proches"),
            ('0', u"Arrondir à l'euro le plus proche"),
            ('1', u"Arrondir aux 10 centimes les plus proches"),
        ], string=u"Précision d'arrondi", default='0')
    of_client_view = fields.Boolean(string='Vue client/vendeur', related="order_id.of_client_view")

    @api.depends('line_ids.prix_total_ttc_simul', 'line_ids.prix_total_ht_simul')
    def _compute_montant_simul(self):
        for wizard in self:
            lines = wizard.line_ids
            total_achat = wizard.order_id.of_total_cout
            total_vente = sum(lines.mapped('prix_total_ht_simul'))

            wizard.marge_simul = total_vente - total_achat
            wizard.pc_marge_simul = 100 * (1 - total_achat / total_vente) if total_vente else -100
            wizard.montant_total_ttc_simul = sum(lines.mapped('prix_total_ttc_simul'))
            wizard.montant_total_ht_simul = sum(lines.mapped('prix_total_ht_simul'))

    @api.multi
    def name_get(self):
        return [
            (record.id,
             "Gestion prix %s %s" % (
                 record.order_id.state == 'draft' and 'devis' or 'commande',
                 record.order_id.name))
            for record in self]

    def bouton_simuler(self):
        self.calculer(True)

    def bouton_valider(self):
        self.calculer(False)

    @api.model
    def bouton_annuler(self):
        return {'type': 'ir.actions.client', 'tag': 'history_back'}

    @api.model
    def _calcule_vals_ligne(self, order_line, to_distribute, total, currency, rounding, line_rounding):
        """
        Cette fonction calcule le nouveau montant à allouer à la ligne de commande passée en paramètre.
        Elle retourne un dictionnaire des valeurs à modifier sur cette ligne.
        @param order_line: Ligne de commande dont on veut ajuster le prix
        @param to_distribute: Montant restant à distribuer
        @param total: Montant actuel cumulé des lignes de commande non encore recalculées
        @param rounding: Booleen déterminant si le prix unitaire doit être arrondi
        @param line_rounding: Règle d'arrondi sur le montant total de la ligne
               {'field': self.arrondi_mode, 'precision': int(self.arrondi_prec)} ou False
        """
        if to_distribute == 0.0:
            line_vals = {'price_unit': 0.0}
            taxes = order_line.tax_id.with_context(base_values=(0.0, 0.0, 0.0))
            taxes = taxes.compute_all(
                0.0, currency, order_line.product_uom_qty, product=order_line.product_id,
                partner=order_line.order_id.partner_id)
        else:
            # Prix HT unitaire final de la ligne
            taxes = order_line.tax_id
            if total == 0.0:  # Permet de gérer les lignes de remises avec montant HT initial de 0
                if self._context.get('pc_marge'):  # Dans le cas d'un calcul de % de marge on part du montant HT
                    taxes_percentage = 0.0
                else:  # Dans tout les autres cas, on part du montant TTC
                    taxes_percentage = sum(taxes.mapped('amount')) / 100
                price_unit = (order_line.price_unit or 1.0) * to_distribute / (1 + taxes_percentage)
            else:
                price_unit = (order_line.price_unit or 1.0) * to_distribute / total
            if rounding:
                price_unit = currency.round(price_unit)

            # Ces deux lignes sont copiées depuis la fonction sale_order_line._compute_amount() d module sale
            price = price_unit * (1 - (order_line.discount or 0.0) / 100.0) * order_line.product_uom_qty
            taxes = taxes.with_context(base_values=(price, price, price)).compute_all(
                price, currency, order_line.product_uom_qty, product=order_line.product_id,
                partner=order_line.order_id.partner_id
            )

            if line_rounding:
                # On arrondit les montants par ligne
                montant = taxes['base']
                if line_rounding['field'] == 'total_included':
                    montant += sum(tax['amount'] for tax in taxes['taxes'])

                montant_arrondi = round(montant, line_rounding['precision'])
                ratio = montant_arrondi / montant
                price_unit *= ratio
                # Recalcul des taxes pour l'affichage de la simulation
                price = price_unit * (1 - (order_line.discount or 0.0) / 100.0) * order_line.product_uom_qty
                taxes = order_line.tax_id.with_context(base_values=(price, price, price))
                taxes = taxes.compute_all(
                    price, currency, order_line.product_uom_qty, product=order_line.product_id,
                    partner=order_line.order_id.partner_id)
            line_vals = {'price_unit': price_unit}
        return {order_line: line_vals}, taxes

    @api.model
    def _calcule_reset_vals_ligne(self, order_line, line_rounding):
        # Appel à of_get_price_unit() pour recalculer le prix unitaire
        price_unit = order_line.of_get_price_unit()
        if line_rounding:
            price = price_unit * (1 - (order_line.discount or 0.0) / 100.0) * order_line.product_uom_qty
            taxes = order_line.tax_id.with_context(base_values=(price, price, price), round=False)
            taxes = taxes.compute_all(
                price, order_line.currency_id, order_line.product_uom_qty, product=order_line.product_id,
                partner=order_line.order_id.partner_id)

            # On arrondit les montants par ligne
            montant = taxes[line_rounding['field']]
            montant_arrondi = round(montant, line_rounding['precision'])
            ratio = montant_arrondi / montant
            price_unit *= ratio

        # Calcul des taxes pour l'affichage de la simulation
        price = price_unit * (1 - (order_line.discount or 0.0) / 100.0) * order_line.product_uom_qty
        taxes = order_line.tax_id.with_context(base_values=(price, price, price))
        taxes = taxes.compute_all(
            price, order_line.currency_id, order_line.product_uom_qty, product=order_line.product_id,
            partner=order_line.order_id.partner_id)
        return {order_line: {'price_unit': price_unit}}, taxes

    @api.model
    def _get_ordered_lines(self, lines):
        # On applique les nouveaux prix sur les lignes dans l'ordre décroissant de quantité vendue.
        # Cela permet d'ajuster plus facilement le prix sur les dernières lignes
        return lines.sorted('quantity', reverse=True)

    @api.multi
    def _appliquer(self, values):
        for line, vals in values.iteritems():
            line.write(vals)

    @api.multi
    def calculer(self, simuler=False):
        """
        Calcule les nouveaux prix des articles sélectionnés en fonction de la méthode de calcul choisie.
        """
        self.ensure_one()

        order = self.order_id
        cur = order.pricelist_id.currency_id
        round_tax = self.env.user.company_id.tax_calculation_rounding_method != 'round_globally'

        lines_select = self.line_ids.filtered(lambda line: line.state == 'included' and line.order_line_id.price_unit)
        if not lines_select:
            # Toutes les lignes sélectionnées ont un prix unitaire à 0
            lines_select = self.line_ids.filtered(lambda line: line.state == 'included')

        nb_select = len(lines_select)
        lines_forced = self.line_ids.filtered(lambda line: line.state == 'forced')
        lines_excluded = self.line_ids - lines_select - lines_forced

        # Les totaux des lignes non sélectionnées sont gardés en précision standard
        total_ht_excluded = sum(lines_excluded.mapped('order_line_id').mapped('price_subtotal'))
        total_ttc_excluded = sum(lines_excluded.mapped('prix_total_ttc'))

        # Les totaux des lignes forcées sont gardés en précision standard
        for lf in lines_forced:
            lf.prix_total_ttc_simul = lf.prix_total_ttc * (lf.prix_total_ht_simul / lf.prix_total_ht)
        total_ht_forced = sum(lines_forced.mapped('prix_total_ht_simul'))
        total_ttc_forced = sum(lines_forced.mapped('prix_total_ttc_simul'))

        total_ht_nonselect = total_ht_excluded + total_ht_forced
        total_ttc_nonselect = total_ttc_excluded + total_ttc_forced

        # Les totaux des lignes sélectionnées sont calculés en précision maximale
        total_ttc_select = total_ht_select = 0.0
        line_taxes = {}
        for line in lines_select.with_context(round=False):
            # Calcul manuel des taxes avec context['round']==False pour conserver la précision des calculs
            order_line = line.order_line_id
            price = order_line.price_unit * (1 - (order_line.discount or 0.0) / 100.0)
            taxes = order_line.tax_id.compute_all(
                price, order_line.currency_id, order_line.product_uom_qty, product=order_line.product_id,
                partner=order_line.order_id.partner_id)
            if line.state == 'included':
                total_ttc_select += taxes['total_included']
                total_ht_select += taxes['total_excluded']
                line_taxes[line.id] = taxes

        # On récupère les données du wizard et vérifie les données saisies par l'utilisateur
        if self.methode_remise == 'prix_ttc_cible':
            if self.valeur <= 0:
                raise UserError(u"(Erreur #RG105)\nVous devez saisir un montant total TTC cible.")
        elif self.methode_remise == 'prix_ht_cible':
            if self.valeur <= 0:
                raise UserError(u"(Erreur #RG105)\nVous devez saisir un montant total HT cible.")
        elif self.methode_remise == 'montant_ttc':
            if not self.valeur:
                raise UserError(u"(Erreur #RG115)\nVous devez saisir un montant TTC à déduire.")
            if self.valeur > self.montant_total_ttc_initial:
                raise UserError(
                    u"(Erreur #RG120)\n"
                    u"Le montant TTC à déduire est supérieur au montant total TTC des articles"
                    u"sur lesquels s'appliquent la remise.")
        elif self.methode_remise == 'montant_ht':
            if not self.valeur:
                raise UserError(u"(Erreur #RG115)\nVous devez saisir un montant HT à déduire.")
            if self.valeur > self.montant_total_ht_initial:
                raise UserError(
                    u"(Erreur #RG120)\n"
                    u"Le montant HT à déduire est supérieur au montant total HT des articles"
                    u"sur lesquels s'appliquent la remise.")
        elif self.methode_remise == 'pc':
            if not 0 < self.valeur <= 100:
                raise UserError(
                    u"(Erreur #RG125)\nLe pourcentage de remise doit être supérieur à 0 et inférieur ou égal à 100.")
        elif self.methode_remise == 'pc_marge':
            if self.valeur >= 100:
                raise UserError(u"(Erreur #RG130)\nLe pourcentage de marge doit être inférieur à 100.")
        elif self.methode_remise == 'reset':
            pass
        else:
            return False

        total_select = total_ttc_select
        tax_field = 'total_included'

        # On détermine le montant TTC cible en fonction de la méthode de calcul choisie
        if self.methode_remise == 'prix_ttc_cible':
            total = self.valeur - total_ttc_nonselect
        elif self.methode_remise == 'prix_ht_cible':
            total = self.valeur - total_ht_nonselect
            total_select = total_ht_select
        elif self.methode_remise == 'montant_ttc':
            total = total_ttc_select - self.valeur
        elif self.methode_remise == 'montant_ht':
            total = total_ht_select - self.valeur
            total_select = total_ht_select
        elif self.methode_remise == 'pc':
            total = total_ttc_select * (1 - self.valeur / 100.0)
        elif self.methode_remise == 'pc_marge':
            # Attention : dans ce cas particulier le total est HT
            total = (100 * order.of_total_cout) / (100.0 - self.valeur) - total_ht_nonselect
            total_select = total_ht_select
            tax_field = 'total_excluded'
            self = self.with_context(pc_marge=True)
        else:
            total = False

        # On applique les nouveaux prix sur les lignes dans l'ordre décroissant de quantité vendue.
        # Cela permet d'ajuster plus facilement le prix sur les dernières lignes
        lines_select = self._get_ordered_lines(lines_select)

        values = {}
        to_distribute = total
        if self.arrondi_mode == 'no':
            line_rounding = False
        else:
            if not self.arrondi_prec:
                raise UserError("Vous devez sélectionner la précision de l'arrondi")
            line_rounding = {'field': self.arrondi_mode, 'precision': int(self.arrondi_prec)}

        for line in lines_select:
            order_line = line.order_line_id
            if self.methode_remise == 'reset':
                vals, taxes = self._calcule_reset_vals_ligne(order_line, line_rounding=line_rounding)
            else:
                vals, taxes = self._calcule_vals_ligne(
                    order_line,
                    to_distribute,
                    total_select,
                    currency=cur,
                    # On arrondit toutes les lignes sauf la dernière
                    rounding=line != lines_select[-1],
                    line_rounding=line_rounding)
            # Recalcul de 'total_excluded' et 'total_included' sans les arrondis
            if not round_tax:
                amount_tax = sum(tax['amount'] for tax in taxes['taxes'])
                taxes.update({'total_excluded': taxes['base'], 'total_included': taxes['base'] + amount_tax})

            if self.methode_remise != 'reset':
                to_distribute -= taxes[tax_field]
                total_select -= line_taxes[line.id][tax_field]
                nb_select -= 1

            values.update(vals)

            # Mise à jour du prix simulé dans la ligne du wizard
            line.prix_total_ht_simul = taxes['total_excluded']
            line.prix_total_ttc_simul = taxes['total_included']

        for line in lines_excluded:
            line.prix_total_ht_simul = line.order_line_id.price_subtotal
            line.prix_total_ttc_simul = line.order_line_id.price_total

        for line in lines_forced:
            line_vals = {'price_unit': line.prix_total_ht_simul}
            vals = {line.order_line_id: line_vals}
            values.update(vals)

        # Pour une simulation, le travail s'arrête ici
        if simuler:
            return

        total_ttc_init = order.amount_total
        self._appliquer(values)
        total_ttc_fin = order.amount_total

        # On ajoute le libellé de la remise dans les notes du devis si case cochée
        if self.afficher_remise:
            text = u"Remise exceptionnelle déduite de %s.\n"
            text = text % (format_amount(self.env, total_ttc_init - total_ttc_fin, cur))
            order.note = text + (order.note or '')
        order.write({'of_echeance_line_ids': order._of_compute_echeances()})

    @api.multi
    def bouton_inclure_tout(self):
        self.line_ids.filtered(lambda l: not l.state == 'included' and not l.product_forbidden_discount).\
            write({'state': 'included'})

    @api.multi
    def bouton_exclure_tout(self):
        self.line_ids.filtered(lambda l: l.state == 'included').write({'state': 'excluded'})

    def toggle_view(self):
        """ Permet de basculer entre la vue vendeur/client
        """
        self.of_client_view = not self.of_client_view

    @api.multi
    def imprimer_gestion_prix(self):
        return self.env['report'].get_action(self, 'of_sale.of_report_saleorder_gestion_prix')

    @api.multi
    def get_lines(self):
        self.ensure_one()
        return self.line_ids.filtered(lambda l: l.state == 'included')

    @api.model
    def of_get_report_name(self, docs):
        return 'Feuille de marge'

    @api.model
    def of_get_report_number(self, docs):
        return ' / '.join(docs.mapped('order_id').mapped('name'))

    @api.model
    def of_get_report_date(self, docs):
        return ' / '.join([
            fields.Date.to_string(fields.Date.from_string(gestion.order_id.confirmation_date)) or
            fields.Date.to_string(fields.Date.from_string(gestion.order_id.date_order)) for gestion in docs
            ])

    def get_recap(self):
        order_lines = self.line_ids.filtered(lambda l: l.state == 'included').mapped('order_line_id')
        order_lines_product = order_lines.filtered(lambda l: l.product_id.type != 'service')
        order_lines_service = order_lines.filtered(lambda l: l.product_id.type == 'service')
        currency_symbol = self.currency_id.symbol
        res = []
        for name, lines in [
                ('Produits', order_lines_product),
                ('Services', order_lines_service),
                ('Total', order_lines)]:
            lines_dict = {'name': name}
            total_achat = sum(lines.mapped('purchase_price'))
            total_vente = sum(lines.mapped('price_subtotal'))
            lines_dict['cout'] = "%0.2f %s" % (total_achat, currency_symbol)
            lines_dict['vente'] = "%0.2f %s" % (total_vente, currency_symbol)
            lines_dict['marge'] = "%0.2f %s" % (total_vente - total_achat, currency_symbol)
            lines_dict['marge_pc'] = ("%0.2f %%" % (100 * (1 - total_achat / total_vente))) if total_vente else "- %"
            res.append(lines_dict)
        return res


class GestionPrixLine(models.TransientModel):
    """Liste des lignes dans le wizard"""
    _name = 'of.sale.order.gestion.prix.line'
    _description = u"Sélection des produits d'un devis/bon de commande"

    # @todo: Déselectionner les lignes dont la quantité ou le prix valent 0
    state = fields.Selection(
        selection=[('excluded', u"Exclus"), ('included', u"Inclus"), ('forced', u"Forcé")],
        string=u"État", required=True, default='included')
    wizard_id = fields.Many2one('of.sale.order.gestion.prix', required=True, ondelete='cascade')
    order_line_id = fields.Many2one(
        'sale.order.line', string="Article", required=True, readonly=True, ondelete='cascade'
    )
    currency_id = fields.Many2one(related='order_line_id.currency_id')
    quantity = fields.Float(string=u"Quantité", related='order_line_id.product_uom_qty', readonly=True)

    cout = fields.Monetary(u'Coût', compute='_compute_cout')
    prix_unit_ht = fields.Monetary(
        string='Prix unit. HT initial', related='order_line_id.price_reduce_taxexcl', readonly=True
    )
    prix_unit_ttc = fields.Monetary(
        string='Prix unit. TTC initial', related='order_line_id.price_reduce_taxinc', readonly=True
    )
    prix_total_ht = fields.Monetary(
        string='Prix total HT initial', related='order_line_id.price_subtotal', readonly=True
    )
    prix_total_ttc = fields.Monetary(
        string='Prix total TTC initial', related='order_line_id.price_total', readonly=True
    )
    remise = fields.Float(related='order_line_id.discount', readonly=True)

    prix_total_ttc_simul = fields.Float(string=u"Prix total TTC simulé", compute='_compute_prix_total_ttc_simul')
    prix_total_ht_simul = fields.Float(string=u"Prix total HT simulé")
    marge = fields.Float(string=u"Marge HT", compute='_compute_marge_simul')
    pc_marge = fields.Float(string=u"% Marge", compute='_compute_marge_simul')
    of_client_view = fields.Boolean(string='Vue client/vendeur', related="wizard_id.of_client_view")

    product_forbidden_discount = fields.Boolean(
        related='order_line_id.product_id.of_forbidden_discount', string=u"Remise interdite pour ce produit")

    @api.depends('order_line_id')
    def _compute_cout(self):
        for line in self:
            order_line = line.order_line_id
            line.cout = order_line.purchase_price * order_line.product_uom_qty

    @api.depends('prix_total_ht_simul')
    def _compute_marge_simul(self):
        for line in self:
            achat = line.cout
            vente = line.prix_total_ht_simul

            line.marge = vente - achat
            if vente:
                line.pc_marge = 100 * (1 - achat / vente)

    @api.depends('prix_total_ht_simul', 'prix_total_ht')
    def _compute_prix_total_ttc_simul(self):
        for line in self:
            if line.prix_total_ht:
                factor = line.prix_total_ht_simul / line.prix_total_ht
                line.prix_total_ttc_simul = line.prix_total_ttc * factor

    @api.onchange('pc_marge')
    def _onchange_pc_marge(self):
        if self.env.context.get("skip_onchange"):
            # Do not skip next onchange
            self.env.context = self.with_context(skip_onchange=False).env.context
        else:
            for line in self:
                # La marge ne peut pas être supérieure ou égale à 100%, sauf si le cout est nul
                if line.cout == 0:
                    pc_marge_max = 100
                else:
                    pc_marge_max = 99.99
                if line.pc_marge > pc_marge_max:
                    line.pc_marge = pc_marge_max

                self.env.context = self.with_context(skip_onchange=True).env.context
                line.prix_total_ht_simul = line.cout and line.cout * (100 / (100 - line.pc_marge))

    @api.onchange('prix_total_ht_simul')
    def _onchange_prix_total_ht_simul(self):
        if self.env.context.get("skip_onchange"):
            # Do not skip next onchange
            self.env.context = self.with_context(skip_onchange=False).env.context
        else:
            for line in self:
                self.env.context = self.with_context(skip_onchange=True).env.context
                line.pc_marge = 100 * (1 - line.cout / line.prix_total_ht_simul) if line.prix_total_ht_simul else -100


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def button_gestion_prix(self):
        self.ensure_one()

        remise_obj = self.env['of.sale.order.gestion.prix']

        line_vals = []
        for line in self.order_line:
            values = {
                'order_line_id': line.id,
                'state': 'included' if
                not line.of_product_forbidden_discount
                and bool(line.product_uom_qty and line.price_unit)
                else 'excluded',
                'prix_total_ht_simul': line.price_subtotal,
                'prix_total_ttc_simul': line.price_total,
            }
            # Création des lignes en base de données pour avoir un id et que les boutons de sélection fonctionnent
            line_vals.append((0, 0, values))

        remise = remise_obj.create({
            'order_id': self.id,
            'line_ids': line_vals,
        })

        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'of.sale.order.gestion.prix',
            'res_id': remise.id,
            'target': 'current',
            'flags': {'initial_mode': 'edit', 'form': {'action_buttons': True, 'options': {'mode': 'edit'}}},
            'context': {'invoice_status': self.invoice_status}
        }
