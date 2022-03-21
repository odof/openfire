# -*- coding: utf-8 -*-

from odoo import models, fields, api
import odoo.addons.decimal_precision as dp


class OFWorktopConfiguratorMaterial(models.Model):
    _name = 'of.worktop.configurator.material'
    _description = u"Matériau pour le configurateur de plan de travail"
    _order = 'sequence'

    name = fields.Char(string=u"Nom", required=True)
    sequence = fields.Integer(string=u"Séquence")
    unit_weight = fields.Float(string=u"Poids au cm³ (kg)", digits=(10, 5), required=True)
    cut_to_size_coeff = fields.Float(
        string=u"Coefficient 'Cut to Size'", required=True, default=1.0,
        help=u"Si le plateau fait moins de 2m², ce coefficient sera appliqué au tarif de la pièce")


class OFWorktopConfiguratorFinishing(models.Model):
    _name = 'of.worktop.configurator.finishing'
    _description = u"Finition pour le configurateur de plan de travail"
    _order = 'sequence'

    name = fields.Char(string=u"Nom", required=True)
    sequence = fields.Integer(string=u"Séquence")


class OFWorktopConfiguratorColor(models.Model):
    _name = 'of.worktop.configurator.color'
    _description = u"Couleur pour le configurateur de plan de travail"
    _order = 'name'

    name = fields.Char(string=u"Nom", required=True)
    image_file = fields.Binary(string=u"Fichier image", attachment=True)
    image_filename = fields.Char(string=u"Nom du fichier image", size=64)


class OFWorktopConfiguratorThickness(models.Model):
    _name = 'of.worktop.configurator.thickness'
    _description = u"Épaisseur & type de chant pour le configurateur de plan de travail"
    _order = 'sequence'

    name = fields.Char(string=u"Nom", required=True)
    sequence = fields.Integer(string=u"Séquence")
    value = fields.Float(string=u"Valeur en cm", required=True)


class OFWorktopConfiguratorService(models.Model):
    _name = 'of.worktop.configurator.service'
    _description = u"Prestation pour le configurateur de plan de travail"
    _order = 'sequence'

    @api.model_cr_context
    def _auto_init(self):
        cr = self._cr
        # Lors de la 1ère mise à jour après la refonte des prestations (févr. 2022), on migre les données existantes.
        cr.execute("SELECT 1 FROM information_schema.columns "
                   "WHERE table_name = 'of_worktop_configurator_service'")
        existe_avant = bool(cr.fetchall())

        res = super(OFWorktopConfiguratorService, self)._auto_init()

        cr.execute("SELECT 1 FROM information_schema.columns "
                   "WHERE table_name = 'of_worktop_configurator_service'")
        existe_apres = bool(cr.fetchall())

        # Si le modèle of_worktop_configurator_service n'existe pas avant et existe après la mise à jour,
        # c'est qu'on est à la 1ère mise à jour après la refonte du modèle de prestation,
        # on doit faire la migration des données.
        if not existe_avant and existe_apres:
            cr.execute("INSERT INTO of_worktop_configurator_service ("
                       "    name, "
                       "    sequence, "
                       "    price, "
                       "    blocking, "
                       "    blocking_message"
                       ") "
                       "SELECT "
                       "    name, "
                       "    sequence, "
                       "    price, "
                       "    blocking, "
                       "    blocking_message "
                       "FROM of_worktop_configurator_distance")
        return res

    name = fields.Char(string=u"Nom", required=True)
    sequence = fields.Integer(string=u"Séquence")
    price = fields.Float(string=u"Tarif")
    blocking = fields.Boolean(string=u"Bloquant")
    blocking_message = fields.Char(string=u"Message de blocage")
    payment_term_id = fields.Many2one(comodel_name='account.payment.term', string=u"Conditions de règlement")
    comment_template2_id = fields.Many2one(comodel_name='base.comment.template', string=u"Modèle de commentaire du bas")


class OFWorktopConfiguratorDiscount(models.Model):
    _name = 'of.worktop.configurator.discount'
    _description = u"Remise pour le configurateur de plan de travail"
    _order = 'sequence'

    name = fields.Char(string=u"Nom", required=True)
    sequence = fields.Integer(string=u"Séquence")
    value = fields.Float(string=u"Valeur", required=True, help=u"Valeur de la remise exprimée en pourcentage")
    pricelist_ids = fields.Many2many(comodel_name='product.pricelist', string=u"Listes de prix", required=True)


class OFWorktopConfiguratorPrice(models.Model):
    _name = 'of.worktop.configurator.price'
    _description = u"Tarif pour le configurateur de plan de travail"
    _order = 'material_id, finishing_id'

    material_id = fields.Many2one(comodel_name='of.worktop.configurator.material', string=u"Matériau", required=True)
    finishing_id = fields.Many2one(comodel_name='of.worktop.configurator.finishing', string=u"Finition", required=True)
    color_ids = fields.Many2many(comodel_name='of.worktop.configurator.color', string=u"Couleurs", required=True)
    thickness_id = fields.Many2one(
        comodel_name='of.worktop.configurator.thickness', string=u"Épaisseur & type de chant", required=True)
    price = fields.Float(string=u"Tarif HT", digits=dp.get_precision('Product Price'))
    pricelist_ids = fields.Many2many(comodel_name='product.pricelist', string=u"Listes de prix", required=True)


class OFWorktopConfiguratorType(models.Model):
    _name = 'of.worktop.configurator.type'
    _description = u"Type de pièce pour le configurateur de plan de travail"
    _order = 'sequence'

    name = fields.Char(string=u"Nom", required=True)
    sequence = fields.Integer(string=u"Séquence")
    material_ids = fields.Many2many(
        comodel_name='of.worktop.configurator.material', relation='of_worktop_configurator_type_material_rel',
        column1='type_id', column2='material_id', string=u"Matériaux", required=True)
    finishing_ids = fields.Many2many(
        comodel_name='of.worktop.configurator.finishing', relation='of_worktop_configurator_type_finishing_rel',
        column1='type_id', column2='finishing_id', string=u"Finitions", required=True)
    product_id = fields.Many2one(comodel_name='product.product', string=u"Article", required=True)
    layout_category_id = fields.Many2one(comodel_name='sale.layout_category', string=u"Section")
    product_line_ids = fields.One2many(
        comodel_name='of.worktop.configurator.type.product.line', inverse_name='type_id',
        string=u"Accessoires & Prestations")


class OFWorktopConfiguratorTypeProductLine(models.Model):
    _name = 'of.worktop.configurator.type.product.line'
    _description = u"Ligne d'article des types de pièce pour le configurateur de plan de travail"
    _order = 'sequence'

    type_id = fields.Many2one(
        comodel_name='of.worktop.configurator.type', string=u"Type de pièce", required=True, index=True,
        ondelete='cascade')
    sequence = fields.Integer(string=u"Séquence")
    product_id = fields.Many2one(comodel_name='product.product', string=u"Article", required=True)
    product_name = fields.Char(
        related='product_id.product_tmpl_id.name', string=u"Nom de l'article", readonly=True, store=True)
    material_id = fields.Many2one(comodel_name='of.worktop.configurator.material', string=u"Matériau", required=True)
    price = fields.Float(string=u"Tarif")


class OFWorktopConfiguratorTax(models.Model):
    _name = 'of.worktop.configurator.tax'
    _description = u"Position fiscale du configurateur"
    _order = 'sequence'

    sequence = fields.Integer(string=u"Séquence")
    fiscal_position_id = fields.Many2one(
        comodel_name='account.fiscal.position', string=u"Position fiscale", required=True, ondelete='cascade')
    pricelist_ids = fields.Many2many(comodel_name='product.pricelist', string=u"Listes de prix", required=True)
