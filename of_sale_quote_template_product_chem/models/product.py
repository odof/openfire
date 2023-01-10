# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def quote_template_description_fields(self):
        # Si l'on modifie un des champs suivants, la description sur les ligne de modèle de devis sera modifiée
        fields_list = super(ProductTemplate, self).quote_template_description_fields() or []
        fields_list += [
            'of_flamme_verte',
            'of_equivalence_flamme_verte',
            'of_eco_label',
            'of_puissance_nom',
            'of_rendement',
            'of_emission_co',
            'of_emission_co_mg',
            'of_emission_poussiere',
            'of_emission_nox',
            'of_cog_emission',
            'of_cov_emission',
            'of_indice_i',
            'of_efficacite_saison',
            'of_fonds_air_bois',
        ]
        return fields_list
