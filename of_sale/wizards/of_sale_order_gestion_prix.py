# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError
from odoo.tools import float_compare

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
            ('pc', u'% de remise globale'),
        ]
        if self.user_has_groups('of_sale.of_group_sale_marge_manager'):
            liste.append(('pc_marge', '% marge'))
        liste.append(('reset', 'remettre au prix magasin'))  # Avec application de la liste de prix du client
        return liste

    order_id = fields.Many2one('sale.order', string='Devis/commande', required=True, ondelete='cascade')
    discount_mode = fields.Selection([
        ('line', "Appliquer la gestion de prix dans les lignes"),
        ('total', "Appliquer la gestion de prix dans les totaux"),
        ], string="Mode de remise", required=True, default='line')
    discount_product_id = fields.Many2one(comodel_name='product.product', string="Article de remise")
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
    cout_total_ht_simul = fields.Monetary(
        string=u'Coût Total HT simulé', digits=dp.get_precision('Sale Price'), compute='_compute_montant_simul')
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
    cost_prorata = fields.Selection(selection=[
        ('price', u"Prix de vente"),
        ('cost', u"Coût"),
    ], default='price', required=True, string=u"Prorata")
    of_client_view = fields.Boolean(string='Vue client/vendeur', related="order_id.of_client_view")

    @api.depends('line_ids.prix_total_ttc_simul', 'line_ids.prix_total_ht_simul', 'line_ids.cout_total_ht_simul')
    def _compute_montant_simul(self):
        for wizard in self:
            lines = wizard.line_ids
            total_achat = sum(lines.mapped('cout_total_ht_simul'))
            total_vente = sum(lines.mapped('prix_total_ht_simul'))

            wizard.marge_simul = total_vente - total_achat
            wizard.pc_marge_simul = 100 * (1 - total_achat / total_vente) if total_vente else -100
            wizard.montant_total_ttc_simul = sum(lines.mapped('prix_total_ttc_simul'))
            wizard.montant_total_ht_simul = sum(lines.mapped('prix_total_ht_simul'))
            wizard.cout_total_ht_simul = sum(lines.mapped('cout_total_ht_simul'))

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

    @api.multi
    def bouton_annuler(self):
        return {'type': 'ir.actions.client', 'tag': 'history_back'}

    @api.multi
    def _appliquer(self, values):
        line_obj = self.env['sale.order.line']
        for line, vals in values.iteritems():
            if isinstance(line, int):
                # Une ligne de remise à créer
                line_obj.create(vals)
            else:
                line.write(vals)

    @api.multi
    def _calculer(self, total, mode, currency, cost_prorata, line_rounding):
        # on conserve la fonction de calcul des prix simulés, pour se servir des résultats pour les montant de remise
        # puis on réinitialise les montants simulés des lignes pour ne pas induire en erreur les utilisateurs
        # ne pas créer de ligne de remise quand on remet au prix magasin
        res = self.line_ids.distribute_amount(total, mode, currency, cost_prorata, line_rounding)
        if self.discount_mode == 'total' and self.methode_remise != 'reset':
            old_res = res
            res = {}

            fake_id = 1
            tax_dict = {}
            # grouper les lignes par taxes. On utilise des tuples pour ne pas qu'une ligne se retrouve dans 2 groupes
            for product_line in self.line_ids.filtered(lambda l: not l.is_discount and l.state == 'included'):
                tax_tup = tuple(product_line.order_line_id.tax_id.ids)
                if tax_tup in tax_dict:
                    tax_dict[tax_tup] |= product_line
                else:
                    tax_dict[tax_tup] = product_line

            for tax_tup, associated_lines in tax_dict.iteritems():
                price_unit = 0
                uom = self.env.ref('product.product_uom_unit')
                for order_line in associated_lines.mapped('order_line_id'):
                    vals = old_res[order_line]
                    price_unit -= (order_line.price_unit - vals['price_unit']) * \
                        (1 - (order_line.discount or 0.0) / 100.0) * \
                        order_line.product_uom._compute_quantity(order_line.product_uom_qty, uom)

                line_vals = {
                    'wizard_id': self.id,
                    'is_discount': True,
                    'discount_tax_ids': [(6, 0, list(tax_tup))],
                    'prix_unit_create': price_unit,
                }
                new_line = self.env['of.sale.order.gestion.prix.line'].new(line_vals)
                new_line.prix_total_ht_simul = sum(
                    associated_lines.mapped('prix_total_ht_simul')) - sum(
                    associated_lines.mapped('order_line_id.price_subtotal'))
                new_line.prix_total_ttc_simul = sum(
                    associated_lines.mapped('prix_total_ttc_simul')) - sum(
                    associated_lines.mapped('order_line_id.price_total'))

                res[fake_id] = new_line.get_values_order_line_create()
                self.line_ids |= new_line
                fake_id += 1

            for product_line in self.line_ids.filtered(lambda l: not l.is_discount and l.state == 'included'):
                product_line.prix_total_ht_simul = product_line.prix_total_ht
                product_line.prix_total_ttc_simul = product_line.prix_total_ttc
                product_line.cout_total_ht_simul = product_line.cout_total_ht

            for forced_line in self.line_ids.filtered(lambda l: not l.is_discount and l.state == 'forced'):
                if forced_line.order_line_id in old_res:
                    res[forced_line.order_line_id] = old_res[forced_line.order_line_id]

        return res

    @api.multi
    def calculer(self, simuler=False):
        """
        Calcule les nouveaux prix des articles sélectionnés en fonction de la méthode de calcul choisie.
        """
        self.ensure_one()

        # supprimer la ligne de remise éventuellement existante
        self.line_ids.filtered(lambda l: l.is_discount).unlink()

        # On récupère les données du wizard et vérifie les données saisies par l'utilisateur
        if self.methode_remise == 'prix_ttc_cible':
            if self.valeur <= 0:
                raise UserError(u"(Erreur #RG205)\nVous devez saisir un montant total TTC cible.")
        elif self.methode_remise == 'prix_ht_cible':
            if self.valeur <= 0:
                raise UserError(u"(Erreur #RG105)\nVous devez saisir un montant total HT cible.")
        elif self.methode_remise == 'montant_ttc':
            if not self.valeur:
                raise UserError(u"(Erreur #RG210)\nVous devez saisir un montant TTC à déduire.")
            if self.valeur > self.montant_total_ttc_initial:
                raise UserError(
                    u"(Erreur #RG215)\n"
                    u"Le montant TTC à déduire est supérieur au montant total TTC des articles"
                    u"sur lesquels s'applique la remise.")
        elif self.methode_remise == 'montant_ht':
            if not self.valeur:
                raise UserError(u"(Erreur #RG110)\nVous devez saisir un montant HT à déduire.")
            if self.valeur > self.montant_total_ht_initial:
                raise UserError(
                    u"(Erreur #RG115)\n"
                    u"Le montant HT à déduire est supérieur au montant total HT des articles"
                    u"sur lesquels s'applique la remise.")
        elif self.methode_remise == 'pc':
            if not 0 < self.valeur <= 100:
                raise UserError(
                    u"(Erreur #RG305)\nLe pourcentage de remise doit être supérieur à 0 et inférieur ou égal à 100.")
        elif self.methode_remise == 'pc_marge':
            if self.valeur >= 100:
                raise UserError(u"(Erreur #RG405)\nLe pourcentage de marge doit être inférieur à 100.")
        elif self.methode_remise == 'reset':
            pass
        else:
            return False

        # Paramètre d'arrondi
        if self.arrondi_mode == 'no':
            line_rounding = False
        else:
            if not self.arrondi_prec:
                raise UserError(u"Vous devez sélectionner la précision de l'arrondi")
            line_rounding = {'field': self.arrondi_mode, 'precision': int(self.arrondi_prec)}

        # On détermine le montant TTC cible en fonction de la méthode de calcul choisie
        order = self.order_id
        # tax_field = 'total_included'
        if self.methode_remise == 'prix_ttc_cible':
            mode = 'ttc'
            total = self.valeur
        elif self.methode_remise == 'prix_ht_cible':
            mode = 'ht'
            total = self.valeur
        elif self.methode_remise == 'montant_ttc':
            mode = 'ttc'
            total = order.amount_total - self.valeur
        elif self.methode_remise == 'montant_ht':
            mode = 'ht'
            total = order.amount_untaxed - self.valeur
        elif self.methode_remise == 'pc':
            mode = 'ttc'
            total = order.amount_total * (1 - self.valeur / 100.0)
        elif self.methode_remise == 'pc_marge':
            mode = 'ht'
            total = (100 * order.of_total_cout) / (100.0 - self.valeur)
            # tax_field = 'total_excluded'
            self = self.with_context(pc_marge=True)
        else:
            mode = 'reset'
            total = False

        cur = order.pricelist_id.currency_id
        cost_prorata = self.methode_remise in [
            'prix_ttc_cible', 'prix_ht_cible', 'montant_ttc', 'montant_ht'] and self.cost_prorata or 'price'
        values = self._calculer(total, mode, cur, cost_prorata, line_rounding)

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
            total_achat = 0.0
            for line in lines:
                total_achat += line.purchase_price * line.product_uom_qty
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
        comodel_name='sale.order.line', string="Article", readonly=True, ondelete='cascade'
    )
    product_id = fields.Many2one(comodel_name='product.product', string="Article", compute='_compute_product_id')
    name = fields.Char(string="Name", compute='_compute_product_id')
    currency_id = fields.Many2one(related='order_line_id.currency_id')
    quantity = fields.Float(string=u"Quantité", compute='_compute_quantity')
    tax_ids = fields.Many2many(
        comodel_name='account.tax', string="Taxe", relation='of_sale_order_gestion_prix_line_discount_tax_rel',
        column1='line_id', column2='tax_id', compute='_compute_tax_ids')

    cout_total_ht = fields.Monetary(u'Coût total HT initial', compute='_compute_prices')
    prix_unit_ht = fields.Monetary(
        string='Prix unit. HT initial', compute='_compute_prices')
    prix_unit_ttc = fields.Monetary(
        string='Prix unit. TTC initial', compute='_compute_prices')
    prix_total_ht = fields.Monetary(
        string='Prix total HT initial', compute='_compute_prices')
    prix_total_ttc = fields.Monetary(
        string='Prix total TTC initial', compute='_compute_prices')
    remise = fields.Float(related='order_line_id.discount', readonly=True)

    prix_total_ttc_simul = fields.Float(string=u"Prix total TTC simulé", readonly=True)
    prix_total_ht_simul = fields.Float(string=u"Prix total HT simulé")
    cout_total_ht_simul = fields.Float(string=u"Coût total HT simulé", readonly=True)
    marge = fields.Float(string=u"Marge HT", compute='_compute_marge_simul')
    pc_marge = fields.Float(string=u"% Marge", compute='_compute_marge_simul')
    of_client_view = fields.Boolean(string='Vue client/vendeur', related="wizard_id.of_client_view")

    discount_tax_ids = fields.Many2many(
        comodel_name='account.tax', string="Taxe", relation='of_sale_order_gestion_prix_line_discount_tax_rel',
        column1='line_id', column2='tax_id')
    is_discount = fields.Boolean(string="Est une ligne de remise")
    # champ pour conserver le prix unitaire calculé, pour la création de ligne de commande
    prix_unit_create = fields.Monetary(string='Prix prix unitaire pour la création de ligne de commande')
    product_forbidden_discount = fields.Boolean(
        related='order_line_id.of_product_forbidden_discount', string=u"Remise interdite pour cet article",
        readonly=True)

    @api.depends('order_line_id', 'is_discount', 'discount_tax_ids')
    def _compute_product_id(self):
        for line in self:
            if not line.is_discount:
                line.product_id = line.order_line_id.product_id.id
                line.name = line.order_line_id.name
            else:
                line.product_id = line.wizard_id.discount_product_id.id
                line.name = "%s (%s)" % (
                    line.wizard_id.discount_product_id.name, " + ".join(line.discount_tax_ids.mapped('name')))

    @api.depends('order_line_id', 'is_discount')
    def _compute_quantity(self):
        for line in self:
            if line.is_discount:
                line.quantity = 1
            else:
                line.quantity = line.order_line_id.product_uom_qty

    @api.depends('order_line_id', 'discount_tax_ids')
    def _compute_tax_ids(self):
        for line in self:
            if line.order_line_id:
                line.tax_ids = line.order_line_id.tax_id.ids
            else:
                line.tax_ids = line.discount_tax_ids.ids

    @api.depends('order_line_id', 'is_discount')
    def _compute_prices(self):
        for product_line in self.filtered(lambda l: not l.is_discount):
            order_line = product_line.order_line_id
            product_line.cout_total_ht = order_line.purchase_price * order_line.product_uom_qty
            product_line.prix_unit_ht = order_line.price_reduce_taxexcl
            product_line.prix_unit_ttc = order_line.price_reduce_taxinc
            product_line.prix_total_ht = order_line.price_subtotal
            product_line.prix_total_ttc = order_line.price_total

    @api.depends('prix_total_ht_simul', 'cout_total_ht_simul')
    def _compute_marge_simul(self):
        for line in self:
            achat = line.cout_total_ht_simul
            vente = line.prix_total_ht_simul

            line.marge = vente - achat
            if vente:
                line.pc_marge = 100 * (1 - achat / vente)

    @api.onchange('pc_marge')
    def _onchange_pc_marge(self):
        for line in self:
            # La marge ne peut pas être supérieure ou égale à 100%, sauf si le cout est nul
            if line.cout_total_ht == 0:
                pc_marge_max = 100
            else:
                pc_marge_max = 99.99
            if line.pc_marge > pc_marge_max:
                line.pc_marge = pc_marge_max

            pc_marge = 100 * (1 - line.cout_total_ht_simul / line.prix_total_ht_simul) if line.prix_total_ht_simul else\
                -100
            if float_compare(pc_marge, line.pc_marge, precision_rounding=0.01):
                line.prix_total_ht_simul = line.cout_total_ht_simul and line.cout_total_ht_simul * \
                    (100 / (100 - line.pc_marge))
                factor = line.prix_total_ht_simul / line.prix_total_ht
                line.prix_total_ttc_simul = line.prix_total_ttc * factor

    @api.onchange('prix_total_ht_simul')
    def _onchange_prix_total_ht_simul(self):
        for line in self:
            total_ht = line.cout_total_ht_simul and line.cout_total_ht_simul * (100 / (100 - line.pc_marge))
            if float_compare(total_ht, line.prix_total_ht_simul, precision_rounding=0.01):
                line.pc_marge = 100 * (1 - line.cout_total_ht_simul / line.prix_total_ht_simul)\
                    if line.prix_total_ht_simul else -100

    @api.multi
    def get_distributed_amount(self, to_distribute, total, currency, cost_prorata, rounding, line_rounding, all_zero):
        """
        Cette fonction calcule le nouveau montant à allouer à la ligne de commande passée en paramètre.
        Elle retourne un dictionnaire des valeurs à modifier sur cette ligne.
        @param order_line: Ligne de commande dont on veut ajuster le prix
        @param to_distribute: Montant restant à distribuer
        @param total: Montant actuel cumulé des lignes de commande non encore recalculées
        @param currency: Monnaie utilisée
        :param cost_prorata: La base de calcul pour le prorata. Peut être 'price', 'cost'
         (ou 'total_cost' si of_sale_budget est installé)
        @param rounding: Booleen déterminant si le prix unitaire doit être arrondi
        @param line_rounding: Règle d'arrondi sur le montant total de la ligne
               {'field': self.arrondi_mode, 'precision': int(self.arrondi_prec)} ou False
        """
        self.ensure_one()
        order_line = self.order_line_id
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
                else:  # Dans tous les autres cas, on part du montant TTC
                    taxes_percentage = sum(taxes.mapped('amount')) / 100
                price_unit = self.get_base_amount(order_line, cost_prorata, all_zero) * \
                    to_distribute / (1 + taxes_percentage)
            else:
                price_unit = self.get_base_amount(order_line, cost_prorata, all_zero) * to_distribute / total
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
                if float_compare(montant_arrondi, montant, precision_rounding=0.01):
                    ratio = montant_arrondi / montant
                    price_unit *= ratio
                    # Recalcul des taxes pour l'affichage de la simulation
                    price = price_unit * (1 - (order_line.discount or 0.0) / 100.0) * order_line.product_uom_qty
                    taxes = order_line.tax_id.with_context(base_values=(price, price, price))
                    taxes = taxes.compute_all(
                        price, currency, order_line.product_uom_qty, product=order_line.product_id,
                        partner=order_line.order_id.partner_id)

            price_management_variation = price_unit - order_line.price_unit + order_line.of_price_management_variation
            new_price_variation = price_management_variation - (price_unit * (order_line.discount or 0.0) / 100.0)

            line_vals = {'price_unit': price_unit,
                         'of_price_management_variation': price_management_variation,
                         'of_unit_price_variation': new_price_variation}
        return {order_line: line_vals}, taxes

    @api.multi
    def get_reset_amount(self, line_rounding):
        self.ensure_one()
        order_line = self.order_line_id
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

        new_price_variation = -price_unit * (order_line.discount or 0.0) / 100.0
        return (
            {order_line: {
                'price_unit': price_unit,
                'of_price_management_variation': 0.0,
                'of_unit_price_variation': new_price_variation,
                'purchase_price': order_line.product_id.get_cost(),
             }},
            taxes)

    @api.multi
    def get_sorted(self):
        # On applique les nouveaux prix sur les lignes dans l'ordre décroissant de quantité vendue.
        # Cela permet d'ajuster plus facilement le prix sur les dernières lignes
        return self.sorted('quantity', reverse=True)

    @api.multi
    def distribute_amount(self, to_distribute, mode, currency, cost_prorata, line_rounding):
        u"""
        Fonction de distribution d'un montant sur les différentes lignes du wizard.
        Cette fonction modifie directement les lignes du wizard et retourne les valeurs à modifier
        sur le bon de commande
        :param to_distribute: Montant à distribuer
        :param mode: Type de manipulation. Peut être 'ht', 'ttc' ou 'reset'
        :param currency: Monnaie utilisée
        :param cost_prorata: La base de calcul pour le prorata. Peut être 'price', 'cost'
         (ou 'total_cost' si of_sale_budget est installé)
        :param line_rounding: Règle d'arrondi sur le montant total de la ligne
               {'field': wizard.arrondi_mode, 'precision': int(wizard.arrondi_prec)} ou False
        """
        round_tax = self.env.user.company_id.tax_calculation_rounding_method != 'round_globally'

        lines_select = self.filtered(lambda line: line.state == 'included')
        if mode != 'reset':
            lines_select = lines_select.filtered(lambda line: line.order_line_id.price_unit) or lines_select
        lines_forced = self.filtered(lambda line: line.state == 'forced')
        lines_excluded = self - lines_select - lines_forced

        # Les totaux des lignes non sélectionnées sont gardés en précision standard
        if mode == 'ht':
            total_excluded = sum(lines_excluded.mapped('order_line_id').mapped('price_subtotal'))
            tax_field = 'total_excluded'
        else:
            total_excluded = sum(lines_excluded.mapped('prix_total_ttc'))
            tax_field = 'total_included'

        values = {}

        # Les totaux des lignes forcées sont gardés en précision standard
        order_lines = lines_select.with_context(round=False).mapped('order_line_id')
        all_zero = False
        # Vérification si toutes les lignes sont a 0 en fonction du prorata choisi
        if cost_prorata == 'cost':
            all_zero = all(purchase_price == 0.0 for purchase_price in order_lines.mapped('purchase_price'))
        elif cost_prorata == 'price':
            all_zero = all(price_unit == 0.0 for price_unit in order_lines.mapped('price_unit'))
        total_forced = 0
        for lf in lines_forced:
            vals, taxes = lf.get_distributed_amount(
                lf.prix_total_ht_simul,
                lf.cout_total_ht if cost_prorata != 'price' else lf.prix_total_ht,
                currency=currency,
                cost_prorata=cost_prorata,
                rounding=True,
                line_rounding=False,
                all_zero=True)

            if not round_tax:
                amount_tax = sum(tax['amount'] for tax in taxes['taxes'])
                taxes.update({'total_excluded': taxes['base'], 'total_included': taxes['base'] + amount_tax})

            values.update(vals)

            # Mise à jour du prix simulé dans la ligne du wizard
            lf.prix_total_ht_simul = taxes['total_excluded']
            lf.prix_total_ttc_simul = taxes['total_included']
            total_forced += taxes[tax_field]

        total_nonselect = total_excluded + total_forced

        # Les totaux des lignes sélectionnées sont calculés en précision maximale
        total_select = 0.0
        line_taxes = {}
        for line in lines_select.with_context(round=False):
            # Calcul manuel des taxes avec context['round']==False pour conserver la précision des calculs
            order_line = line.order_line_id
            price = self.get_base_amount(order_line, cost_prorata, all_zero) * \
                (1 - (order_line.discount or 0.0) / 100.0)
            taxes = order_line.tax_id.compute_all(
                price, order_line.currency_id, order_line.product_uom_qty, product=order_line.product_id,
                partner=order_line.order_id.partner_id)
            total_select += taxes[tax_field]
            line_taxes[line.id] = taxes

        # On applique les nouveaux prix sur les lignes dans l'ordre décroissant de quantité vendue.
        # Cela permet d'ajuster plus facilement le prix sur les dernières lignes
        lines_select = lines_select.get_sorted()

        to_distribute -= total_nonselect
        for line in lines_select:
            if mode == 'reset':
                vals, taxes = line.get_reset_amount(line_rounding=line_rounding)
                line.cout_total_ht_simul = \
                    line.order_line_id.product_id.get_cost() * line.order_line_id.product_uom_qty
            else:
                vals, taxes = line.get_distributed_amount(
                    to_distribute,
                    total_select,
                    currency=currency,
                    cost_prorata=cost_prorata,
                    # On arrondit toutes les lignes sauf la dernière
                    rounding=line != lines_select[-1],
                    line_rounding=line_rounding,
                    all_zero=all_zero)
            # Recalcul de 'total_excluded' et 'total_included' sans les arrondis
            if not round_tax:
                amount_tax = sum(tax['amount'] for tax in taxes['taxes'])
                taxes.update({'total_excluded': taxes['base'], 'total_included': taxes['base'] + amount_tax})

            if mode != 'reset':
                to_distribute -= taxes[tax_field]
                total_select -= line_taxes[line.id][tax_field]

            values.update(vals)

            # Mise à jour du prix simulé dans la ligne du wizard
            line.prix_total_ht_simul = taxes['total_excluded']
            line.prix_total_ttc_simul = taxes['total_included']

        for line in lines_excluded:
            line.prix_total_ht_simul = line.order_line_id.price_subtotal
            line.prix_total_ttc_simul = line.order_line_id.price_total
        return values

    @api.model
    def get_base_amount(self, order_line, cost_prorata, all_zero):
        """
        @param order_line: La ligne de commande sur laquelle on récupère les informations
        @param cost_prorata: Le type de prorata utilisé
        @param all_zero: Vrai si cost_prorata == 'cost' et tout les purchase price sont a 0,
                              si cost_prorata == 'price' et tout les price unit sont a 0,
                         Faux dans les autres cas
        """
        if cost_prorata == 'cost':
            return order_line.purchase_price or all_zero and 1.0 or 0.0
        else:
            return order_line.price_unit or all_zero and 1.0 or 0.0

    @api.multi
    def get_values_order_line_create(self):
        self.ensure_one()
        if not self.is_discount:
            return {}
        res = {
            'order_id': self.wizard_id.order_id.id,
            'name': self.name,
            'product_id': self.product_id.id,
            'product_uom': self.env.ref('product.product_uom_unit').id,
            'price_unit': self.prix_unit_create,
            'tax_id': [(6, 0, [self.discount_tax_ids.ids])],
            'customer_lead': 0,
        }
        return res


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
                'cout_total_ht_simul': line.purchase_price * line.product_uom_qty,
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
