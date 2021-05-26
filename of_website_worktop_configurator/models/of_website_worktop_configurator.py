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
    _order = 'sequence'

    name = fields.Char(string=u"Nom", required=True)
    sequence = fields.Integer(string=u"Séquence")
    image_file = fields.Binary(string=u"Fichier image", attachment=True)
    image_filename = fields.Char(string=u"Nom du fichier image", size=64)


class OFWorktopConfiguratorGroup(models.Model):
    _name = 'of.worktop.configurator.group'
    _description = u"Groupe pour le configurateur de plan de travail"
    _order = 'sequence'

    name = fields.Char(string=u"Nom", required=True)
    sequence = fields.Integer(string=u"Séquence")
    color_ids = fields.Many2many(comodel_name='of.worktop.configurator.color', string=u"Couleurs")
    pricelist_ids = fields.Many2many(comodel_name='product.pricelist', string=u"Listes de prix")


class OFWorktopConfiguratorThickness(models.Model):
    _name = 'of.worktop.configurator.thickness'
    _description = u"Épaisseur pour le configurateur de plan de travail"
    _order = 'sequence'

    name = fields.Char(string=u"Nom", required=True)
    sequence = fields.Integer(string=u"Séquence")
    value = fields.Float(string=u"Valeur en cm", required=True)


class OFWorktopConfiguratorEdgeType(models.Model):
    _name = 'of.worktop.configurator.edge.type'
    _description = u"Type de chant pour le configurateur de plan de travail"
    _order = 'sequence'

    name = fields.Char(string=u"Nom", required=True)
    sequence = fields.Integer(string=u"Séquence")


class OFWorktopConfiguratorDistance(models.Model):
    _name = 'of.worktop.configurator.distance'
    _description = u"Distance pour le configurateur de plan de travail"
    _order = 'sequence'

    name = fields.Char(string=u"Nom", required=True)
    sequence = fields.Integer(string=u"Séquence")
    price = fields.Float(string=u"Tarif")
    blocking = fields.Boolean(string=u"Bloquant")
    blocking_message = fields.Char(string=u"Message de blocage")


class OFWorktopConfiguratorPrice(models.Model):
    _name = 'of.worktop.configurator.price'
    _description = u"Tarif pour le configurateur de plan de travail"
    _order = 'material_id, finishing_id, group_id'

    material_id = fields.Many2one(comodel_name='of.worktop.configurator.material', string=u"Matériau", required=True)
    finishing_id = fields.Many2one(comodel_name='of.worktop.configurator.finishing', string=u"Finition", required=True)
    group_id = fields.Many2one(comodel_name='of.worktop.configurator.group', string=u"Groupe", required=True)
    thickness_id = fields.Many2one(comodel_name='of.worktop.configurator.thickness', string=u"Épaisseur", required=True)
    price = fields.Float(string=u"Tarif HT", digits=dp.get_precision('Product Price'))


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
    group_ids = fields.Many2many(
        comodel_name='of.worktop.configurator.group', relation='of_worktop_configurator_type_group_rel',
        column1='type_id', column2='group_id', string=u"Groupes", required=True)
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
