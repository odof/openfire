# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OFSupplierEdi(models.Model):
    _name = 'of.supplier.edi'
    _description = "EDI Fournisseur"
    _order = 'id desc'

    order_id = fields.Many2one(comodel_name='purchase.order', string=u"Commande fournisseur")
    partner_id = fields.Many2one(
        comodel_name='res.partner', related='order_id.partner_id', string=u"Fournisseur", readonly=True)
    edi_file = fields.Binary(related='order_id.of_edi_file', string=u"Fichier EDI", attachment=True)
    edi_filename = fields.Char(related='order_id.of_edi_filename', string=u"Nom du fichier EDI")
    state = fields.Selection(
        selection=[('in_progress', u"En cours"), ('ok', u"OK"), ('error', u"Erreur")], string=u"Statut",
        default='in_progress')
    error_msg = fields.Text(string=u"Message d'erreur")

    @api.multi
    def name_get(self):
        res = []
        for edi in self:
            partner_name = edi.partner_id.name
            date_string = fields.Datetime.from_string(edi.create_date).strftime("%d/%m/%Y %H:%M:%S")
            res.append((edi.id, partner_name + " - " + date_string))
        return res
