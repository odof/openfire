# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OFWebsiteProductFuel(models.Model):
    _name = 'of.website.product.fuel'
    _description = u"""Combustible pour le site internet"""

    name = fields.Char(string=u"Nom", required=True)
    line_ids = fields.One2many(comodel_name='of.website.product.fuel.line', inverse_name='fuel_id', string=u"Lignes")


class OFWebsiteProductFuelLine(models.Model):
    _name = 'of.website.product.fuel.line'
    _description = u"""Ligne de combustible pour le site internet"""

    fuel_id = fields.Many2one(comodel_name='of.website.product.fuel', string=u"Combustible", required=True)
    product_id = fields.Many2one(comodel_name='product.product', string=u"Article", required=True)
    length = fields.Char(string=u"Longueur")
    split = fields.Boolean(string=u"Fendu")


class OFWebsiteProductFuelCheckoutMode(models.Model):
    _name = 'of.website.product.fuel.checkout.mode'
    _description = u"""Mode de retrait de combustible pour le site internet"""

    name = fields.Char(string=u"Nom", required=True)
    type = fields.Selection(
        selection=[('delivery', u"Livraison"),
                   ('storage', u"Stockage")])
    pellets_drive = fields.Boolean(string=u"Retrait borne Pellets Drive")
    product_id = fields.Many2one(comodel_name='product.product', string=u"Article")
    line_ids = fields.One2many(
        comodel_name='of.website.product.fuel.checkout.mode.line', inverse_name='mode_id', string=u"Lignes")


class OFWebsiteProductFuelCheckoutModeLine(models.Model):
    _name = 'of.website.product.fuel.checkout.mode.line'
    _description = u"""Ligne de mode de retrait de combustible pour le site internet"""

    mode_id = fields.Many2one(
        comodel_name='of.website.product.fuel.checkout.mode', string=u"Mode de retrait", required=True)
    product_id = fields.Many2one(comodel_name='product.product', string=u"Article", required=True)
    min_distance = fields.Float(string=u"Distance min (km)")
    max_distance = fields.Float(string=u"Distance max (km)")

