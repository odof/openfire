# -*- coding: utf-8 -*-

from odoo import api, models, fields


class OfPlanningInterventionTemplate(models.Model):
    _inherit = 'of.planning.intervention.template'

    # Parc installe - base of_service_parc_installe
    fi_parc = fields.Boolean(string=u"PARC INSTALLÉ")
    fi_parc_name = fields.Boolean(string=u"N° de série")
    fi_parc_product_id = fields.Boolean(string="Produit")
    fi_parc_modele = fields.Boolean(string=u"Modèle")
    fi_parc_brand_id = fields.Boolean(string="Marque")
    fi_parc_product_category_id = fields.Boolean(string=u"Catégorie")
    fi_parc_date_installation = fields.Boolean(string="Date d'installation")
    fi_parc_installation = fields.Boolean(string="Installation")
    fi_parc_conforme = fields.Boolean(string="Conforme")
    fi_parc_installateur_id = fields.Boolean(string="Installateur")
    fi_parc_note = fields.Boolean(string="Note")

    # Parc installe - base of_service_parc_installe
    ri_parc = fields.Boolean(string=u"PARC INSTALLÉ")
    ri_parc_name = fields.Boolean(string=u"N° de série")
    ri_parc_product_id = fields.Boolean(string="Produit")
    ri_parc_modele = fields.Boolean(string=u"Modèle")
    ri_parc_brand_id = fields.Boolean(string="Marque")
    ri_parc_product_category_id = fields.Boolean(string=u"Catégorie")
    ri_parc_date_installation = fields.Boolean(string="Date d'installation")
    ri_parc_installation = fields.Boolean(string="Installation")
    ri_parc_conforme = fields.Boolean(string="Conforme")
    ri_parc_installateur_id = fields.Boolean(string="Installateur")
    ri_parc_note = fields.Boolean(string="Note")

    # onchange Parc installé
    @api.onchange('fi_parc')
    def _onchange_fi_parc(self):
        values = {}
        if self.fi_parc:
            rdv_keys = [key for key in self._fields.keys() if key.startswith("fi_parc_")]
            for key in rdv_keys:
                values[key] = True
            self.update(values)

    @api.onchange('ri_parc')
    def _onchange_ri_parc(self):
        values = {}
        if self.ri_parc:
            rdv_keys = [key for key in self._fields.keys() if key.startswith("ri_parc_")]
            for key in rdv_keys:
                values[key] = True
            self.update(values)
