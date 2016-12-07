# -*- coding: utf-8 -*-

from openerp import models, fields

class of_pret_appareil(models.Model):
    "Appareils prêtés"
    _name = "of.pret.appareil"

    name = fields.Char(u'No de série', required=True)
    modele_id = fields.Many2one('of.product.modele', string='Modèle', required=True, ondelete='restrict', index=True)
    note = fields.Text(u'Note')
    of_pret_appareil_line_ids = fields.One2many('of.pret.appareil.line', 'appareil_id', "Prêts de l'appareil")
    date_pret = fields.Date(u'Date dernier prêt', related="of_pret_appareil_line_ids.date_pret", store=True)
    date_retour = fields.Date(u'Date dernier retour', related="of_pret_appareil_line_ids.date_retour", store=True)


class of_pret_appareil_line(models.Model):
    "Historique prêts appareils"
    _name = "of.pret.appareil.line"

    appareil_id = fields.Many2one('of.pret.appareil', string='Appareil', ondelete='cascade', index=True)
    client_id = fields.Many2one('res.partner', 'Client', required=True, domain="[('parent_id','=',False)]", ondelete='restrict')
    site_depot_id = fields.Many2one('res.partner', 'Site de dépôt', domain="['|',('parent_id','=',client_id),('id','=',client_id)]", ondelete='restrict')
    site_depot_id_address = fields.Char('Adresse dépôt', related='site_depot_id.contact_address')
    date_pret = fields.Date(u'Date de prêt', required=True)
    date_retour = fields.Date(u'Date de retour')
    note = fields.Text(u'Note')

    _order = "date_pret desc, date_retour"
