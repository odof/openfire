# -*- coding: utf-8 -*-

from openerp import models, fields


class res_company(models.Model):
    _inherit = "res.company"
    
    of_num_nne = fields.Char("Numéro national d'émetteur (NNE)", size=6, required=False, help=u"Numéro national d'émetteur pour opérations bancaires par échange de fichiers informatiques")
    of_num_ics = fields.Char("Identifiant créancier SEPA (ICS)", size=32, required=False, help=u"Identifiant créancier SEPA (ICS) pour opérations bancaires SEPA par échange de fichiers informatiques")
    

class res_partner(models.Model):
    _inherit = "res.partner"
    
    of_sepa_rum = fields.Char("Référence unique du mandat (RUM) SEPA", size=35, required=False, help=u"Référence unique du mandat (RUM) SEPA pour opérations bancaires par échange de fichiers informatiques")
    of_sepa_date_mandat = fields.Date("Date de signature du mandat SEPA", required=False, help=u"Date de signature du mandat SEPA pour opérations bancaires par échange de fichiers informatiques")
    of_sepa_type_prev = fields.Selection([("FRST","1er prélèvement récurrent à venir"),("RCUR","Prélèvement récurrent en cours")], 'Type de prélèvement (SEPA)', required=True, help=u"Type de prélèvement SEPA.\n- Mettre à 1er prélèvement quand aucun prélèvement n'a été effectué avec ce mandat.\nLors d'un 1er prélèvement, cette option passera automatiquement à prélèvement récurrent en cours.\n\n- Mettre à prélèvement récurrent en cours lorsqu'un prélèvement a déjà été effectué avec ce mandat.\n\n")
    company_registry = fields.Char(u'Registre de la société', size=64) # Migration : on ajoute le champ company_registry pour les partenaires. Il est définit dans of_sales mais on le rajoute au cas où of_sales ne serait pas installé.
    
    _defaults = {
        'of_sepa_type_prev': 'FRST'
    }
