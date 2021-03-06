# -*- coding: utf-8 -*-

from odoo import api, fields, models


class OFProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model_cr_context
    def _auto_init(self):
        """
        Mise en place d'une valeur par défaut pour la description vente des marques de produit
        """
        cr = self._cr
        cr.execute(
            "SELECT * FROM information_schema.columns WHERE table_name = '%s' AND column_name = 'of_flamme_verte'" %
            (self._table,))
        exists = bool(cr.fetchall())
        res = super(OFProductTemplate, self)._auto_init()
        if not exists:
            product_brands = self.env['of.product.brand'].with_context(active_test=False).search([])
            for product_brand in product_brands:
                product_brand.write({'description_sale': """% if object.norme_id:
Norme : ${object.norme_id.name or ""}
% if object.of_flamme_verte:
${object.of_flamme_verte}${'\u2605'}
% endif
% if object.of_equivalence_flamme_verte:
Équivalence flamme verte : ${object.of_equivalence_flamme_verte}${'\u2605'}
% endif
% if object.of_eco_label:
Éco-label : ${object.of_eco_label}
% endif
% if object.of_puissance_nom:
Puissance nominale : ${object.of_puissance_nom} kW
% endif
% if object.of_rendement:
Rendement : ${object.of_rendement} %
% endif
% if object.of_emission_co:
Émission CO : ${object.of_emission_co} % à 13% d'O2
% endif
% if object.of_emission_poussiere:
Émission de poussière : ${object.of_emission_poussiere} mg/Nm3 à 13% d'O2
% endif
% if object.of_emission_nox:
Émission de NOx : ${object.of_emission_nox} mg/Nm3 à 13% d'O2
% endif
% if object.of_indice_i:
Indice I : ${object.of_indice_i}
% endif
% if object.of_fonds_air_bois:
Éligible Fonds Air Bois
% endif
% endif
% if object.description_sale
${'\\n' + object.description_sale}
% endif"""})
        return res

    of_flamme_verte = fields.Char(string=u"Flamme verte", help=u"Exprimé en nombre d'étoiles")
    of_equivalence_flamme_verte = fields.Char(string=u"Équivalence flamme verte", help=u"Exprimé en nombre d'étoiles")
    of_eco_label = fields.Char(string=u"Éco-label")
    of_puissance_nom = fields.Char(string=u"Puissance nominale", help=u"Exprimé en kW")
    of_rendement = fields.Char(string=u"Rendement", help=u"Exprimé en %")
    of_emission_co = fields.Char(string=u"Émission de CO", help=u"Exprimé en % à 13% d'O2")
    of_emission_poussiere = fields.Char(string=u"Émission de poussière", help=u"Exprimé en mg/Nm3 à 13% d'O2")
    of_emission_nox = fields.Char(string=u"Émission de NOx", help=u"Exprimé en mg/Nm3 à 13% d'O2")
    of_indice_i = fields.Char(string=u"Indice I")
    of_fonds_air_bois = fields.Boolean(string=u"Éligible Fonds Air Bois ?")


class OfProductBrand(models.Model):
    _inherit = 'of.product.brand'

    def _get_default_description_sale(self):
        return """% if object.norme_id:
Norme : ${object.norme_id.name or ""}
% if object.of_flamme_verte:
${object.of_flamme_verte}${'\u2605'}
% endif
% if object.of_equivalence_flamme_verte:
Équivalence flamme verte : ${object.of_equivalence_flamme_verte}${'\u2605'}
% endif
% if object.of_eco_label:
Éco-label : ${object.of_eco_label}
% endif
% if object.of_puissance_nom:
Puissance nominale : ${object.of_puissance_nom} kW
% endif
% if object.of_rendement:
Rendement : ${object.of_rendement} %
% endif
% if object.of_emission_co:
Émission CO : ${object.of_emission_co} % à 13% d'O2
% endif
% if object.of_emission_poussiere:
Émission de poussière : ${object.of_emission_poussiere} mg/Nm3 à 13% d'O2
% endif
% if object.of_emission_nox:
Émission de NOx : ${object.of_emission_nox} mg/Nm3 à 13% d'O2
% endif
% if object.of_indice_i:
Indice I : ${object.of_indice_i}
% endif
% if object.of_fonds_air_bois:
Éligible Fonds Air Bois
% endif
% endif
% if object.description_sale
${'\\n' + object.description_sale}
% endif"""

    description_sale = fields.Text(default=_get_default_description_sale)
