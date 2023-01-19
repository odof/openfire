# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

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
            cr.execute(
                "UPDATE of_product_brand SET description_sale = %s",
                ("""% if object.norme_id:
Norme : ${object.norme_id.name or ""}
% endif
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
% if object.description_sale
${'\\n' + object.description_sale}
% endif""",))
        return res

    of_flamme_verte = fields.Char(string=u"Flamme verte", help=u"Exprimé en nombre d'étoiles")
    of_equivalence_flamme_verte = fields.Char(string=u"Équivalence flamme verte", help=u"Exprimé en nombre d'étoiles")
    of_eco_label = fields.Char(string=u"Éco-label")
    of_puissance_nom = fields.Char(string=u"Puissance nominale", help=u"Exprimé en kW")
    of_rendement = fields.Char(string=u"Rendement", help=u"Exprimé en %")
    of_emission_co = fields.Char(string=u"Émission de CO (%)", help=u"Exprimé en % à 13% d'O2")
    of_emission_co_mg = fields.Char(string=u"Émission de CO (mg/m³)")
    of_emission_poussiere = fields.Char(string=u"Émission de poussière", help=u"Exprimé en mg/Nm3 à 13% d'O2")
    of_emission_nox = fields.Char(string=u"Émission de NOx", help=u"Exprimé en mg/Nm3 à 13% d'O2")
    of_cog_emission = fields.Char(string=u"Émission de COG", help=u"Exprimé en mg/m3")
    of_cov_emission = fields.Char(string=u"Émission de COV", help=u"Exprimé en µg/m3")
    of_indice_i = fields.Char(string=u"Indice I")
    of_efficacite_saison = fields.Char(string=u"% Efficacité énergétique saisonnière")
    of_fonds_air_bois = fields.Boolean(string=u"Éligible Fonds Air Bois ?")


class OfProductBrand(models.Model):
    _inherit = 'of.product.brand'

    @api.model
    def _default_description_sale(self):
        return """% if object.norme_id:
Norme : ${object.norme_id.name or ""}
% endif
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
% if object.of_emission_co_mg:
Émission CO : ${object.of_emission_co_mg} mg/m³
% endif
% if object.of_emission_poussiere:
Émission de poussière : ${object.of_emission_poussiere} mg/Nm3 à 13% d'O2
% endif
% if object.of_emission_nox:
Émission de NOx : ${object.of_emission_nox} mg/Nm3 à 13% d'O2
% endif
% if object.of_cog_emission:
Émission de COG : ${object.of_cog_emission} mg/m3
% endif
% if object.of_cov_emission:
Émission de COV : ${object.of_cov_emission} mg/m3
% endif
% if object.of_indice_i:
Indice I : ${object.of_indice_i}
% endif
% if object.of_efficacite_saison:
Efficacité énergétique saisonnière : ${object.of_efficacite_saison} %
% endif
% if object.of_fonds_air_bois:
Éligible Fonds Air Bois
% endif
% if object.description_sale
${'\\n' + object.description_sale}
% endif"""

    description_sale = fields.Text(default=lambda self: self._default_description_sale())
