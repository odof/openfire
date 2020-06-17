# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    of_supplier_edi = fields.Boolean(related='partner_id.of_supplier_edi', string=u"Fournisseur EDI", readonly=True)
    of_edi = fields.Many2one(comodel_name='of.supplier.edi', string=u"EDI Fournisseur", copy=False)
    of_edi_state = fields.Selection(related='of_edi.state', string=u"État de l'envoi EDI", readonly=True)
    of_edi_file = fields.Binary(string=u"Fichier EDI", attachment=True, copy=False)
    of_edi_filename = fields.Char(string=u"Nom du fichier EDI", copy=False)

    @api.multi
    def action_send_edi(self):
        # EDI
        self = self.sudo()
        for order in self:
            if order.partner_id.of_supplier_edi:
                order.of_edi = self.env['of.supplier.edi'].create({'order_id': order.id})
                order.generate_edi_file()
                if order.of_edi_file:
                    order.send_edi_file()

        return True

    @api.multi
    def generate_edi_file(self):
        """
        Génère le fichier EDI pour le fournisseur - A surcharger
        """
        return True

    @api.multi
    def send_edi_file(self):
        """
        Envoie le fichier EDI au fournisseur - A surcharger
        """
        return True
