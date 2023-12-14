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
Émission CO : ${object.of_emission_co} % à 13% d'O₂
% endif
% if object.of_emission_co_mg:
Émission CO : ${object.of_emission_co_mg} mg/Nm³ à 13% d'O₂
% endif
% if object.of_emission_poussiere:
Émission de poussière : ${object.of_emission_poussiere} mg/Nm³ à 13% d'O₂
% endif
% if object.of_emission_nox:
Émission de NOx : ${object.of_emission_nox} mg/Nm³ à 13% d'O₂
% endif
% if object.of_cog_emission:
Émission de COG : ${object.of_cog_emission} mg/Nm³ à 13% d'O₂
% endif
% if object.of_cov_emission:
Émission de COV : ${object.of_cov_emission} mg/Nm³ à 13% d'O₂
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
% endif""",))
        return res

    of_flamme_verte = fields.Char(string=u"Flamme verte", help=u"Exprimé en nombre d'étoiles")
    of_equivalence_flamme_verte = fields.Char(string=u"Équivalence flamme verte", help=u"Exprimé en nombre d'étoiles")
    of_eco_label = fields.Char(string=u"Éco-label")
    of_puissance_nom = fields.Char(string=u"Puissance nominale", help=u"Exprimé en kW")
    of_rendement = fields.Char(string=u"Rendement", help=u"Exprimé en %")
    of_emission_co = fields.Char(string=u"Émission de CO (%)", help=u"Exprimé en % à 13% d'O₂")
    of_emission_co_mg = fields.Char(string=u"Émission de CO (mg/Nm³)", help=u"Exprimé en mg/Nm³ à 13% d'O₂")
    of_emission_poussiere = fields.Char(string=u"Émission de poussière", help=u"Exprimé en mg/Nm³ à 13% d'O₂")
    of_emission_nox = fields.Char(string=u"Émission de NOx", help=u"Exprimé en mg/Nm³ à 13% d'O₂")
    of_cog_emission = fields.Char(string=u"Émission de COG", help=u"Exprimé en mg/Nm³ à 13% d'O₂")
    of_cov_emission = fields.Char(string=u"Émission de COV", help=u"Exprimé en mg/Nm³ à 13% d'O₂")
    of_indice_i = fields.Char(string=u"Indice I")
    of_efficacite_saison = fields.Char(string=u"% Efficacité énergétique saisonnière")
    of_fonds_air_bois = fields.Boolean(string=u"Éligible Fonds Air Bois ?")


class OfProductBrand(models.Model):
    _inherit = 'of.product.brand'

    @api.model
    def _auto_init(self):
        module_self = self.env['ir.module.module'].search([('name', '=', 'of_product_chem')])
        actions_todo = module_self and module_self.latest_version and module_self.latest_version < "10.0.4.3.0"
        if actions_todo:
            brands = self.search([('description_sale', '!=', False)])
            # Pour chaque marque on essaye de modifier la description pour corriger les différentes unités
            for brand in brands:
                descr = brand.description_sale
                # O2 => O₂
                descr = descr.replace(u"O2", u"O₂")
                # mg/m³ => mg/Nm³
                descr = descr.replace(u"mg/m³", u"mg/Nm³")
                # mg/m3 => mg/Nm³
                descr = descr.replace(u"mg/m3", u"mg/Nm³")
                # mg/Nm3 => mg/Nm³
                descr = descr.replace(u"mg/Nm3", u"mg/Nm³")
                # Émission CO
                starting_index = descr.find(u"Émission CO")
                if starting_index > 0:
                    found_index = descr.find(u"mg/Nm³", starting_index)
                    verify_index = descr.find(u"mg/Nm³ à", starting_index)
                    if found_index > starting_index and found_index != verify_index:
                        new_str = u"mg/Nm³ à 13% d'O₂"
                        special_index = descr.find(u"%s", starting_index)
                        if starting_index < special_index < found_index:
                            new_str = u"mg/Nm³ à 13%% d'O₂"
                        descr = descr[:found_index] + new_str + descr[found_index+6:]
                # COG
                starting_index = descr.find(u"COG")
                if starting_index > 0:
                    found_index = descr.find(u"mg/Nm³", starting_index)
                    verify_index = descr.find(u"mg/Nm³ à", starting_index)
                    if found_index > starting_index and found_index != verify_index:
                        new_str = u"mg/Nm³ à 13% d'O₂"
                        special_index = descr.find(u"%s", starting_index)
                        if starting_index < special_index < found_index:
                            new_str = u"mg/Nm³ à 13%% d'O₂"
                        descr = descr[:found_index] + new_str + descr[found_index+6:]
                # COV
                starting_index = descr.find(u"COV")
                if starting_index > 0:
                    found_index = descr.find(u"mg/Nm³", starting_index)
                    verify_index = descr.find(u"mg/Nm³ à", starting_index)
                    if found_index > starting_index and found_index != verify_index:
                        new_str = u"mg/Nm³ à 13% d'O₂"
                        special_index = descr.find(u"%s", starting_index)
                        if starting_index < special_index < found_index:
                            new_str = u"mg/Nm³ à 13%% d'O₂"
                        descr = descr[:found_index] + new_str + descr[found_index+6:]
                brand.description_sale = descr
        return super(OfProductBrand, self)._auto_init()

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
Émission CO : ${object.of_emission_co} % à 13% d'O₂
% endif
% if object.of_emission_co_mg:
Émission CO : ${object.of_emission_co_mg} mg/Nm³ à 13% d'O₂
% endif
% if object.of_emission_poussiere:
Émission de poussière : ${object.of_emission_poussiere} mg/Nm³ à 13% d'O₂
% endif
% if object.of_emission_nox:
Émission de NOx : ${object.of_emission_nox} mg/Nm³ à 13% d'O₂
% endif
% if object.of_cog_emission:
Émission de COG : ${object.of_cog_emission} mg/Nm³ à 13% d'O₂
% endif
% if object.of_cov_emission:
Émission de COV : ${object.of_cov_emission} mg/Nm³ à 13% d'O₂
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
