# -*- coding: utf-8 -*-

import logging
import requests
import json

from odoo import models, fields, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class OFWizardPoujoulatCart(models.TransientModel):
    _name = 'of.wizard.poujoulat.cart'

    purchase_id = fields.Many2one(comodel_name='purchase.order')
    line_ids = fields.One2many(comodel_name='of.wizard.poujoulat.cart.item', inverse_name='wizard_id')
    message = fields.Text(string="Message", readonly=True, compute='_compute_message')
    sent = fields.Boolean(string=u"Envoyée vers CatEstimate")
    has_error = fields.Boolean(string=u"Erreur d'envoi")

    @api.depends('line_ids')
    def _compute_message(self):
        poujoulat_brand_ids = self.env['ir.values'].get_default(
            'of.connector.config.settings', 'of_poujoulat_brand_ids') or []
        brands = self.env['of.product.brand'].browse(poujoulat_brand_ids).exists()
        message = (
            u"Seuls les articles des marques configurées seront envoyés. Liste des marques:\n%s"
            % u"\n".join(brands.mapped('name'))
        )
        for record in self:
            final_message = [message]
            products = [
                line.product_id
                for line in record.line_ids
                if not line._get_estimate_values()
            ]
            if products:
                final_message += [
                    u"Les articles suivants ne seront pas envoyés car des informations sont manquantes :",
                    u"\n".join(product.display_name for product in products)
                ]
            record.message = u"\n".join(final_message)

    @api.multi
    def action_send_cart(self):
        self.ensure_one()
        ir_values_obj = self.env['ir.values']
        poujoulat_url = ir_values_obj.get_default('of.connector.config.settings', 'of_poujoulat_host')
        redirect_url = ir_values_obj.get_default('of.connector.config.settings', 'of_poujoulat_redirect') or ""
        if not poujoulat_url:
            raise ValidationError(u"Aucune adresse de serveur n'a été configurée pour le connecteur poujoulat.")
        values = {'estimateLines': []}
        headers = {'Content-Type': 'application/json'}
        for line in self.line_ids:
            vals = line._get_estimate_values()
            if line.quantity and vals:
                values['estimateLines'].append(vals)
        has_ipv6 = requests.packages.urllib3.util.connection.HAS_IPV6
        requests.packages.urllib3.util.connection.HAS_IPV6 = False
        data = {}
        try:
            response = requests.post(poujoulat_url, headers=headers, data=json.dumps(values), verify=False)
            data = response.json()
            if response.status_code == 200:
                self.purchase_id.write({'of_poujoulat_sent': True, 'of_poujoulat_error': False})
                self.sent = True
            else:
                self.purchase_id.write({
                    'of_poujoulat_error': u"Code erreur [%s]\n%s" % (response.status_code, response.text)
                })
                self.has_error = True
        except Exception:
            self.purchase_id.write({
                'of_poujoulat_error': u"Code erreur [%s]\n%s" % (response.status_code, response.text)
            })
            self.has_error = True
        finally:
            requests.packages.urllib3.util.connection.HAS_IPV6 = has_ipv6
        if 'redirectionUrl' not in data:
            return {'type': 'ir.actions.do_nothing'}
        return {
            'type': 'ir.actions.act_url',
            'url': redirect_url + data['redirectionUrl'],
            'target': 'new'
        }


class OfWizardModinoxCartItem(models.TransientModel):
    _name = 'of.wizard.poujoulat.cart.item'

    wizard_id = fields.Many2one(comodel_name='of.wizard.poujoulat.cart', required=True, ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string=u"Article", required=True)
    quantity = fields.Float(string=u"Quantité")
    artas400 = fields.Char(string=u"Artas400", related='product_id.of_pou_artas400', readonly=True)
    variante = fields.Integer(string=u"Variante d'article", related='product_id.of_pou_variante', readonly=True)
    cond = fields.Char(string=u"Unité de conditionnement", related='product_id.of_pou_cond', readonly=True)

    @api.multi
    def _get_estimate_values(self):
        self.ensure_one()
        if (
            not self.product_id.of_pou_artas400
            or not self.product_id.of_pou_variante
            or not self.product_id.of_pou_cond
        ):
            return {}
        return {
            'artas400': self.product_id.of_pou_artas400,
            'qte': self.quantity,
            'variante': self.product_id.of_pou_variante,
            'unitCond': self.product_id.of_pou_cond,
        }
