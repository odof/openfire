# -*- encoding: utf-8 -*-

from openerp import models, fields, api
from openerp.exceptions import UserError

class of_product_nomenclature(models.Model):
    "Gestion des nomenclatures de produits"

    _name = 'of.product.nomenclature'
    _description = u"Gestion des nomenclatures de produits"

    name = fields.Char("Nom", size=64, required=True, translate=True)
    of_product_nomenclature_line = fields.One2many('of.product.nomenclature.line', 'nomenclature_id', 'Produits nomenclature', copy=True)
    sequence = fields.Integer('Séquence', help="Définit l'ordre d'affichage des nomenclatures dans les listes (plus petit au début)")
    is_specific = fields.Boolean(string=u"Nomenclature spécifique")

    _order = 'name'
    _sql_constraints = [('number_uniq', 'unique(name)', 'Il existe déjà un enregistrement avec le même nom. (#100)')]

    @api.one
    def copy(self, default=None):
        "Permettre la duplication des nomenclatures produits malgré la contrainte d'unicité du nom (ajout (copie) au nom)"
        if default is None:
            default = {}
        default = default.copy()
        # On se place en utilisateur anglais pour simplifier les calculs de traduction
        self = self.with_context(lang='en_US', of_prefixe_traduction_copie="(copie)")
        default['name'] = '(copie)' + self.name
        return super(of_product_nomenclature, self).copy(default)


class IrTranslation(models.Model):
    _inherit = 'ir.translation'

    @api.model
    def create(self, vals):
        "Pour fonction dupliquer, renomme aussi la traduction avec un préfixe passé dans le contexte [souvent (copie)]"
        prefixe = self._context.get('of_prefixe_traduction_copie')
        if prefixe:
            if vals.get('source'):
                # Définir la valeur du champ source écrase aussi la valeur du champ src
                if 'src' in vals:
                    vals['src'] = prefixe + vals['src']
            if vals.get('value'):
                vals['value'] = prefixe + vals['value']
        return super(IrTranslation, self).create(vals)


class of_product_nomenclature_line(models.Model):
    "Liste des composants nomenclature produit"

    _name = 'of.product.nomenclature.line'
    _description = u"Liste des composants d'une nomenclature"

    @api.depends('prix_ht','quantite')
    def calcul_total_ht(self):
        "Fonction du filed function total_ht"
        for ligne in self:
            ligne.total_ht = ligne.prix_ht * ligne.quantite

    product_id = fields.Many2one('product.template', 'Produit', required=True, ondelete='restrict')
    nomenclature_id = fields.Many2one('of.product.nomenclature', 'Nomenclature', required=True)
    quantite = fields.Integer('Quantité', required=True)
    prix_ht = fields.Float('Prix HT', related='product_id.lst_price')
    total_ht = fields.Float('Total HT', compute='calcul_total_ht', method=True, digits=(16, 2))
    sequence = fields.Integer('Séquence', help="Définit l'ordre d'affichage des produits dans la nomenclature (plus petit au début)")

    _order = 'sequence'
    _defaults = {
        'quantite': 1
    }

    @api.onchange('product_id')
    def onchange_product_nomenclature_line(self):
        result = {}
        produit = self.env['product.template'].browse([self.product_id.id])
        if produit:
            result['prix_ht'] = produit[0].lst_price
        else:
            result['prix_ht'] = 0
        self.prix_ht = result['prix_ht']

######################
###     Wizard     ###
######################

class wizard_of_product_nomenclature(models.TransientModel):
    "Ce wizard permet de mettre des composants d'une nomenclature dans un devis"

    _name = 'of.product.nomenclature.wizard'
    _description = u"Sélectionner des composants d'une nomenclature"
    _rec_name = 'nomenclature_id'

    nomenclature_id = fields.Many2one('of.product.nomenclature', 'Nomenclature')
    nomenclature_line_ids = fields.One2many('of.product.nomenclature.line.wizard', 'nomenclature_id', 'Composants lines', order='sequence')
    active_id_model = fields.Char("Document d'origine", default=lambda self: str(self._context['active_id']) + ',' + self._context['active_model'])

    @api.multi
    def valider(self, context):
        "Bouton valider : on copie les composants sélectionner dans le document (devis/commande ou facture)"

        # On récupère le modèle de document (commande/devis, facture) depuis lequel le wizard est appelé et son id.
        # Nous les avons au préalable mis dans le champ active_id_model (valeur par défaut lors de la création du champ)
        if self.active_id_model:
            active_model = self.active_id_model.split(',')
            if len(active_model):
                active_id = int(active_model[0].strip())
                active_model = active_model[1].strip()
            else:
                return
        else:
            raise UserError("Erreur ! (#NP103)\n\nVous devez sélectionner un document sur lequel vous voulez ajouter les éléments d'une nomenclature.")

        if not active_id or not active_model:
            raise UserError("Erreur ! (#NP105)\n\nVous devez sélectionner un document.")

        if active_model == 'sale.order':
            ligne_obj = self.env['sale.order.line']
            document = self.env['sale.order'].browse(active_id) # Devis/commande sélectionné
        elif active_model == 'account.invoice':
            ligne_obj = self.env['account.invoice.line']
            document = self.env['account.invoice'].browse(active_id) # Facture sélectionnée
        else:
            raise UserError("Erreur ! (#NP108)\n\nVous ne pouvez utiliser les nomenclatures que dans un devis (commande à l'état brouillon) ou une facture.")

        if document.state != 'draft':
            raise UserError("Erreur ! (#NP110)\n\nVous ne pouvez faire une nomenclature sur que sur un document à l'état brouillon.")

        # On parcourt tous les composants sélectionnés dans le wizard
        for composant in self.nomenclature_line_ids: # Données du wizard
            # Si le composant n'est pas sélectionné, on passe au suivant.
            if not composant.selection:
                continue

            doc_ligne = {
                'product_id': composant.product_id.id,
                'product_uom': composant.product_id.uom_id.id,
                'name': composant.product_id.name,
                'price_unit': 0.00
            }

            if active_model == 'sale.order':
                doc_ligne['order_id'] = document.id
                doc_ligne['product_uom_qty'] = composant.quantite
                if document.order_line:
                    doc_ligne['sequence'] = document.order_line[-1].sequence # Pour mettre la ligne à la fin du devis
                # On calcule certaines choses (taux TVA, prix TTC, ...) et on enregistre la ligne
                ligne = self.env['sale.order.line'].create(doc_ligne)
                ligne.product_id_change()

            elif active_model == 'account.invoice':
                doc_ligne['invoice_id'] = document.id
                doc_ligne['quantity'] = composant.quantite
                if document.invoice_line_ids:
                    doc_ligne['sequence'] = document.invoice_line_ids[-1].sequence # Pour mettre la ligne à la fin de la facture
                # On récupère le compte comptable affecté au produit
                doc_ligne['account_id'] = ligne_obj.get_invoice_line_account(document.type, composant.product_id, document.fiscal_position_id, document.company_id).id
                # On calcule certaines choses (taux TVA, prix TTC, ...) et on enregistre la ligne
                ligne = ligne_obj.create(doc_ligne)
                ligne._onchange_product_id()

        if active_model == 'account.invoice':
            document._onchange_invoice_line_ids() # On doit faire recalculer le montant des taxes de l'ensemble de la facture

        return True

    @api.onchange('nomenclature_id')
    def onchange_nomenclature(self):
        if not self.nomenclature_id:
            self.nomenclature_line_ids = [(5,0)]
        nomenclature = self.env['of.product.nomenclature'].browse(self.nomenclature_id.id)
        line_obj = self.env['of.product.nomenclature.line.wizard']
        result = [(5,0)] # On efface les lignes existantes
        # Dans la nomenclature, ce sont les articles de base (product.template) et non les variantes (product.product)
        # On affiche toutes les variantes du produit de base dans le wizard
        for composant in nomenclature.of_product_nomenclature_line: # Parcourt de tous les articles de base de la nomenclature
            # On parcourt toutes les variantes du produit de base
            for variante in self.env['product.product'].search([('product_tmpl_id', '=', composant.product_id.id)]):
                valeurs = {'product_id': variante.id, 'quantite': composant.quantite, 'prix_ht': variante.lst_price}
                result.append((4, line_obj.create(valeurs).id))
        self.nomenclature_line_ids = result

    @api.multi
    def bouton_coche_tout(self):
        "Bouton cocher tous les articles"
        self.nomenclature_line_ids.write({'selection': True})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'of.product.nomenclature.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': self._context
        }

    @api.multi
    def bouton_decocher_tout(self):
        "Bouton décocher tous les articles"
        self.nomenclature_line_ids.write({'selection': False})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'of.product.nomenclature.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': self._context
        }

class wizard_of_product_nomenclature_line(models.TransientModel):
    "Liste des composants sélectionnés d'une nomenclature dans le wizard"

    _name = 'of.product.nomenclature.line.wizard'
    _description = u"Sélection des composants d'une nomenclature"
    _rec_name = 'product_id'

    selection = fields.Boolean(string='Selection composant')
    nomenclature_id = fields.Many2one('of.product.nomenclature.wizard', 'Nomenclature', required=False, invisible="1", ondelete="cascade")
    product_id = fields.Many2one('product.product', 'Produit', required=True, readonly="1", ondelete='restrict')
    quantite = fields.Integer('Quantité', required=True, readonly="1", default=1)
    prix_ht = fields.Float('Prix HT', related='product_id.lst_price', readonly="1")

    _defaults = {
        'selection': False
    }

    @api.multi
    def bouton_coche(self):
        "Coche ligne produit"
        self.write({'selection': True})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'of.product.nomenclature.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': self.nomenclature_id.id,
            'target': 'new',
        }

    @api.multi
    def bouton_decocher(self):
        "Décoche ligne produit"
        self.write({'selection': False})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'of.product.nomenclature.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': self.nomenclature_id.id,
            'target': 'new',
        }

class sale_order(models.Model):
    _inherit = "sale.order"

    @api.multi
    def action_wizard_nomenclature(self):
        wizard_obj = self.env['of.product.nomenclature.wizard']
        wizard_id = wizard_obj.with_context(active_id=self.id, active_ids=[self.id], active_model=self._name).create({}).id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'of.product.nomenclature.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': wizard_id,
            'target': 'new',
            'context': self._context
        }

class account_invoice(models.Model):
    _inherit = "account.invoice"

    @api.multi
    def action_wizard_nomenclature(self):
        wizard_obj = self.env['of.product.nomenclature.wizard']
        wizard_id = wizard_obj.with_context(active_id=self.id, active_ids=[self.id], active_model=self._name).create({}).id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'of.product.nomenclature.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': wizard_id,
            'target': 'new',
            'context': self._context
        }


class ResPartner(models.Model):
    _inherit = 'res.partner'

    of_specific_nomenclature_ids = fields.Many2many(
        comodel_name='of.product.nomenclature', string=u"Nomenclatures restreintes")


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    of_is_custom_made = fields.Boolean(string=u"Article sur mesure")
    of_custom_made_file = fields.Binary(string=u"Fichier explicatif")
    of_custom_made_filename = fields.Char(string=u"Nom du fichier explicatif")
    of_custom_made_parameter_ids = fields.One2many(
        comodel_name='of.product.custom.made.parameter', inverse_name='product_tmpl_id', string=u"Liste des mesures")

    of_color_chart_file = fields.Binary(string=u"Fichier nuancier")
    of_color_chart_filename = fields.Char(string=u"Nom du fichier nuancier")

    of_bloc_option = fields.Boolean(
        string=u"Option de bloc", help=u"Indique que cet article ne peut pas être sélectionné seul dans son bloc")
    of_incompatible_product_ids = fields.Many2many(
        comodel_name='product.template', rel='of_incompatible_product_tmpl_rel', id1='product_tmpl_id',
        id2='incompatible_product_tmpl_id', string=u"Produits incompatibles",
        help=u"Permet d'indiquer une liste de produits incompatibles au sein d'une nomenclature")

    of_shipping_costs_to_define = fields.Boolean(string=u"Frais de port à préciser")


class OFProductCustomMadeParameter(models.Model):
    _name = 'of.product.custom.made.parameter'
    _order = 'sequence'

    product_tmpl_id = fields.Many2one(comodel_name='product.template', string=u"Article")
    sequence = fields.Integer(string=u"Séquence")
    name = fields.Char(string=u"Nom", required=True)
    unit = fields.Char(string=u"Unité de mesure", required=True)
    min_value = fields.Integer(string=u"Valeur minimale", required=True)
    max_value = fields.Integer(string=u"Valeur maximale", required=True)
    not_required = fields.Boolean(string=u"Non obligatoire")


class SaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    def _auto_init(self, cr, context=None):
        res = super(SaleConfiguration, self)._auto_init(cr, context=context)
        if self.pool.get('ir.values').get_default(cr, 1, 'sale.config.settings', 'of_forbidden_delivery_weeks') is None:
            self.pool.get('ir.values').set_default(cr, 1, 'sale.config.settings', 'of_forbidden_delivery_weeks',
                                                   "19,31,32,33,52")
        return res

    of_forbidden_delivery_weeks = fields.Char(string=u"(OF) Semaines de livraison interdites")

    @api.model
    def get_default_sale_config(self, fields):
        res = super(SaleConfiguration, self).get_default_sale_config(fields)
        if 'of_forbidden_delivery_weeks' in fields:
            res['of_forbidden_delivery_weeks'] = self.env['ir.values'].get_default(
                'sale.config.settings', 'of_forbidden_delivery_weeks')
        return res

    @api.multi
    def set_sale_defaults(self):
        res = super(SaleConfiguration, self).set_sale_defaults()
        self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_forbidden_delivery_weeks', self.of_forbidden_delivery_weeks)
        return res
