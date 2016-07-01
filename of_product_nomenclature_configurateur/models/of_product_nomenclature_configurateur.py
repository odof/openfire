# -*- encoding: utf-8 -*-

from openerp import models, fields, api
from openerp.exceptions import UserError
 
class of_product_nomenclature_bloc(models.Model):
    "Gestion des blocs de nomenclatures de produits"
    
    _name = 'of.product.nomenclature.bloc'
    _description = u"Gestion des blocs de nomenclatures de produits"

    name = fields.Char("Nom", size=64, required=True)
    nb_selection_min = fields.Integer('Nb produit sélection minimum', required=True, help="Nombre minimum de produits du bloc qui doivent être sélectionnés")
    nb_selection_max = fields.Integer('Nb produit sélection maximum', required=True, help="Nombre maximum de produits du bloc qui doivent être sélectionnés.")
    sequence = fields.Integer('Séquence', help="Définit l'ordre d'affichage des blocs dans la nomenclature (plus petit au début)")

    _defaults = {
        'nb_selection_min': 1,
        'nb_selection_max': 9999
    }
    _order = 'sequence, name'
    _sql_constraints = [('number_uniq', 'unique(name)', 'Il existe déjà un enregistrement avec le même nom.')]
    
    @api.one
    def copy(self, default=None):
        "Permettre la duplication des blocs de nomenclatures malgré la contrainte d'unicité du nom (ajout (copie) au nom)"
        if default is None:
            default = {}
        default = default.copy()
        default['name'] = self.name + '(copie)'
        return super(of_product_nomenclature_bloc, self).copy(default)


class of_product_nomenclature_line(models.Model):
    "Liste des composants nomenclature produit"
    
    _inherit = 'of.product.nomenclature.line'

    bloc_id = fields.Many2one('of.product.nomenclature.bloc', 'Bloc', required=True)
    
    _order = 'bloc_id, sequence'



######################
###     Wizard     ###
######################

class wizard_of_product_configurateur(models.TransientModel):
    "Ce wizard permet de mettre des composants d'une nomenclature dans un devis"
    
    _name = 'of.product.configurateur.wizard'
    _description = u"Wizard configurateur de produits"
    _rec_name = 'nomenclature_id'
    
    nomenclature_id = fields.Many2one('of.product.nomenclature', 'Nomenclature')
    nomenclature_line_ids = fields.One2many('of.product.configurateur.line.wizard', 'nomenclature_id', 'Composants lines', order='sequence_bloc, sequence_article')
    active_id_model = fields.Char("Document d'origine", default=lambda self: 'active_id' in self._context and str(self._context['active_id']) + ',' + self._context['active_model'])

    @api.multi
    def valider(self, context):
        "Bouton valider : on copie les composants sélectionnés dans le document (devis/commande ou facture)"
         
        def valider_bloc(erreur, texte):
            if nb_selection < nb_selection_min or nb_selection > nb_selection_max:
                erreur = True
                texte += "Bloc " + nom_bloc + " : "
                if nb_selection_min == 1 and nb_selection_max == 1:
                    texte += u"vous devez sélectionner un et un seul article.\n"
                else:
                    texte += u"vous devez sélectionner entre " + str(nb_selection_min) + u" et " + str(nb_selection_max) + u" article(s).\n"
            return erreur, texte

        # On récupère le modèle de document (commande/devis, facture) depuis lequel le wizard est appelé et son id.
        # Nous les avons au préalable mis dans le champ active_id_model (valeur par défaut lors de la création du champ)
        # Si est à False, c'est que nous venons du site internet.
        if self.active_id_model:
            active_model = self.active_id_model.split(',')
            if len(active_model):
                active_id = int(active_model[0].strip())
                active_model = active_model[1].strip()
            else:
                return
        else:
            # On vient du site internet
            active_model = 'res.partner'
            partner_obj = self.env['res.users'].browse(self._uid).partner_id
            #raise UserError("Erreur ! (#NP103)\n\nVous devez sélectionner un document sur lequel vous voulez ajouter les éléments d'une nomenclature.")
        
        #if not active_id or not active_model:
        #    raise UserError("Erreur ! (#NP105)\n\nVous devez sélectionner un document.")
        
        # On vérifie que les conditions de sélection des produits sont respectées.
        
        bloc_id_precedent = ""
        nb_selection = 0
        nb_selection_min = "" # Nb d'article minimum que l'on doit sélectionner du bloc en cours
        nb_selection_max = "" # Idem maximum
        nom_bloc = ""
        texte = ""
        erreur = False
        
        # Vérification des conditions de sélection des produits
        # On parcourt la liste des produits du wizard 
        for composant in self.nomenclature_line_ids:
            # Si nous n'avons pas récupéré les infos des critères de sélection min et max du bloc en cours, on le fait. 
            if not nb_selection_min:
                nb_selection_min = composant.bloc_id.nb_selection_min
                nb_selection_max = composant.bloc_id.nb_selection_max
                nom_bloc = composant.bloc_id.name
                bloc_id_precedent = composant.bloc_id.id
            
            # Si c'est l'article d'un nouveau bloc, on teste si les conditions du bloc précédent sont respectées
            if bloc_id_precedent and composant.bloc_id.id != bloc_id_precedent:
                erreur, texte = valider_bloc(erreur, texte)
                bloc_id_precedent = composant.bloc_id.id
                nb_selection = 0
                nb_selection_min = composant.bloc_id.nb_selection_min
                nb_selection_max = composant.bloc_id.nb_selection_max
                nom_bloc = composant.bloc_id.name
                
            if composant.selection:
                nb_selection = nb_selection + 1
            
        erreur, texte = valider_bloc(erreur, texte) # On valide le dernier bloc
        
        if erreur:
            raise UserError("Erreur !\n\n" + texte)
        
        # Si on vient du site internet.
        # On doit créer une commande avec le partnaire de l'utilisateur
        if active_model == 'res.partner':
            commande = self.env['sale.order'].create({
                'partner_id': partner_obj.id,
            })
        
        if active_model == 'sale.order':
            ligne_obj = self.env['sale.order.line']
            document = self.env['sale.order'].browse(active_id) # Devis/commande sélectionné
        elif active_model == 'res.partner':
            ligne_obj = self.env['sale.order.line']
            document = self.env['sale.order'].browse(commande.id)
        elif active_model == 'account.invoice':
            ligne_obj = self.env['account.invoice.line']
            document = self.env['account.invoice'].browse(active_id) # Facture sélectionnée
        else:
            raise UserError("Erreur ! (#NP108)\n\nVous ne pouvez utiliser le configurateur de produits que dans un devis (commande à l'état brouillon) ou une facture.")

        if document.state != 'draft':
            raise UserError("Erreur ! (#NP110)\n\nVous ne pouvez utiliser le configurateur de produits que sur un document à l'état brouillon.")
   

        
        # On enregistre les produits sélectionnés dans devis/commande/facture
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
            
            elif active_model == 'res.partner':
                # On vient du site internet.
                doc_ligne['order_id'] = document.id
                doc_ligne['product_uom_qty'] = composant.quantite
                if document.order_line:
                    doc_ligne['sequence'] = document.order_line[-1].sequence # Pour mettre la ligne à la fin du devis
                # On calcule certaines choses (taux TVA, prix TTC, ...) et on enregistre la ligne
                ligne = commande.env['sale.order.line'].create(doc_ligne)
                ligne.product_id_change()
            
        if active_model == 'account.invoice':
            document._onchange_invoice_line_ids() # On doit faire recalculer le montant des taxes de l'ensemble de la facture
        
        # On valide le devis si vient du site web
        if active_model == 'res.partner':
            commande.action_confirm()
            
        if active_model == 'res.partner':
            return {
                'type': 'ir.actions.act_url',
                'url': '/my/home',
                'target': 'self'
            }
        else:
            return True
    
    
    @api.onchange('nomenclature_id')
    def onchange_nomenclature(self):
        # On peuple le wizard avec les produits de la nomenclature dès qu'elle est sélectionnée
        if not self.nomenclature_id:
            self.nomenclature_line_ids = [(5,0)]
        nomenclature = self.env['of.product.nomenclature'].browse(self.nomenclature_id.id)
        line_obj = self.env['of.product.configurateur.line.wizard']
        result = [(5,0)] # On efface les lignes existantes
        # Dans la nomenclature, ce sont les articles de base (product.template) et non les variantes (product.product)
        # On affiche toutes les variantes du produit de base dans le wizard
        for composant in nomenclature.of_product_nomenclature_line: # Parcourt de tous les articles de base de la nomenclature
            # On parcourt toutes les variantes du produit de base
            for variante in self.env['product.product'].search([('product_tmpl_id', '=', composant.product_id.id)]):
                valeurs = {'sequence_bloc': composant.bloc_id.sequence, 'sequence_article': composant.sequence, 'bloc_id': composant.bloc_id.id, 'product_id': variante.id, 'quantite': composant.quantite, 'prix_ht': variante.lst_price}
                result.append((4, line_obj.create(valeurs).id))
        self.nomenclature_line_ids = result
     
    @api.multi
    def bouton_coche_tout(self):
        "Bouton cocher tous les articles"
        self.nomenclature_line_ids.write({'selection': True})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'of.product.configurateur.wizard',
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
            'res_model': 'of.product.configurateur.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': self._context
        }


class wizard_of_product_configurateur_line(models.TransientModel):
    "Liste des composants sélectionnés du configurateur dans le wizard"
    
    _name = 'of.product.configurateur.line.wizard'
    _description = u"Wizard configurateur de produits"
    _rec_name = 'product_id'
    
    selection = fields.Boolean(string='Selection composant')
    bloc_id = fields.Many2one('of.product.nomenclature.bloc', 'Bloc', required=True)
    nomenclature_id = fields.Many2one('of.product.configurateur.wizard', 'Nomenclature', required=False, invisible="1", ondelete="cascade")
    product_id = fields.Many2one('product.product', 'Produit', required=True, readonly="1", ondelete='restrict')
    quantite = fields.Integer('Quantité', required=True, readonly="1", default=1)
    prix_ht = fields.Float('Prix HT', related='product_id.lst_price', readonly="1")
    sequence_bloc = fields.Integer('Séquence bloc')
    sequence_article = fields.Integer('Séquence article')
    
    _defaults = {
        'selection': False
    }

    @api.multi
    def bouton_coche(self):
        "Coche ligne produit"
        self.write({'selection': True})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'of.product.configurateur.wizard',
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
            'res_model': 'of.product.configurateur.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': self.nomenclature_id.id,
            'target': 'new',
        }


class sale_order(models.Model):
    _inherit = "sale.order"

    @api.multi
    def action_wizard_configurateur(self):
        wizard_obj = self.env['of.product.configurateur.wizard']
        wizard_id = wizard_obj.with_context(active_id=self.id, active_ids=[self.id], active_model=self._name).create({}).id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'of.product.configurateur.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': wizard_id,
            'target': 'new',
            'context': self._context
        }


class account_invoice(models.Model):
    _inherit = "account.invoice"

    @api.multi
    def action_wizard_configurateur(self):
        wizard_obj = self.env['of.product.configurateur.wizard']
        wizard_id = wizard_obj.with_context(active_id=self.id, active_ids=[self.id], active_model=self._name).create({}).id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'of.product.configurateur.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': wizard_id,
            'target': 'new',
            'context': self._context
        }
