# -*- coding: utf-8 -*-

from openerp import models, fields, api

class of_pret_appareil(models.Model):
    "Appareils prêtés"
    _name = "of.pret.appareil"

    name = fields.Char(u'No de série', required=True)
    modele_id = fields.Many2one('of.product.modele', string='Modèle', required=True, ondelete='restrict', index=True)
    product_category_id = fields.Many2one('product.category', 'Famille')
    marque_id = fields.Many2one('of.product.marque', u"Marque")
    note = fields.Text(u'Note')
    of_pret_appareil_line_ids = fields.One2many('of.pret.appareil.line', 'appareil_id', "Prêts de l'appareil")
    date_pret = fields.Date(u'Date dernier prêt', related="of_pret_appareil_line_ids.date_pret", store=True)
    date_retour = fields.Date(u'Date dernier retour', related="of_pret_appareil_line_ids.date_retour", store=True)
    # Champ partner_id, principalement pour compatibilité avec courriers of_gesdoc
    partner_id = fields.Many2one('res.partner', 'Dernier client', related='of_pret_appareil_line_ids.client_id', readonly=True)
    sav_lie_id = fields.Char(u'Dernier SAV lié', related="of_pret_appareil_line_ids.sav_id.of_code", store=True)


class of_pret_appareil_line(models.Model):
    "Historique prêts appareils"
    _name = "of.pret.appareil.line"

    appareil_id = fields.Many2one('of.pret.appareil', string='Appareil', ondelete='cascade', index=True)
    client_id = fields.Many2one('res.partner', 'Client', required=True, domain="[('parent_id','=',False)]", ondelete='restrict')
    site_depot_id = fields.Many2one('res.partner', 'Site de dépôt', domain="['|',('parent_id','=',client_id),('id','=',client_id)]", ondelete='restrict')
    site_depot_id_address = fields.Char('Adresse dépôt', related='site_depot_id.contact_address')
    date_pret = fields.Date(u'Date de prêt', required=True)
    date_retour = fields.Date(u'Date de retour')
    sav_id = fields.Many2one('project.issue', 'SAV lié')
    note = fields.Text(u'Note')

    _order = "date_pret desc, date_retour"


class project_issue(models.Model):
    _inherit = "project.issue"

    def _calcul_si_pret_appareil(self):
        "field function de of_is_pret_appareil"
        for ligne in self:
            if len(ligne.of_pret_appareil_ids) == 0 or ligne.of_pret_appareil_ids[0].date_retour:
                ligne.of_is_pret_appareil = False
            else:
                ligne.of_is_pret_appareil = True

    of_pret_appareil_ids = fields.One2many('of.pret.appareil.line', 'sav_id', u"Prêts d'appareil")
    of_is_pret_appareil = fields.Boolean(u'Appareil prêté dans le cadre de ce SAV ?', compute='_calcul_si_pret_appareil', help=u"Un appareil a t-il été prêté dans le cadre de ce SAV ?")

    @api.one
    def void(self):
        "Sert quand on clique sur un smart button pour qu'il ne se passe rien."
        return True
