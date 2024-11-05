# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ProductTemplate(models.Model):
    """
    Some fields's names are in French here because they are based on the French "Flamme Verte", "Fond Air Bois" labels
    that are used in the chimney industry. The labels are used to rate the efficiency of a product.
    There is no official translation for these labels in English so we kept the French names for functional reasons.
    """

    _inherit = "product.template"

    of_flamme_verte = fields.Char(string="Flamme Verte", help="Expressed in number of stars")
    of_flamme_verte_equivalence = fields.Char(string="Flamme Verte Equivalence", help="Expressed in number of stars")
    of_eco_label = fields.Char(string="Eco-label")
    of_power_rating = fields.Char(string="Power Rating", help="Expressed in kW")
    of_yield = fields.Char(string="Yield", help="Expressed in %")
    of_co_emission = fields.Char(string="CO Emissions (%)", help="Expressed in % at 13% O₂")
    of_co_mg_emission = fields.Char(string="CO Emissions (mg/Nm³)", help="Expressed in mg/Nm³ at 13% O₂")
    of_dust_emission = fields.Char(string="Dust Emission", help="Expressed in mg/Nm³ at 13% O₂")
    of_nox_emission = fields.Char(string="NOx Emission", help="Expressed in mg/Nm³ at 13% O₂")
    of_goc_emission = fields.Char(string="GOC Emission", help="Expressed in mg/Nm³ at 13% O₂")
    of_voc_emission = fields.Char(string="VOC Emission", help="Expressed in mg/Nm³ at 13% O₂")
    of_i_index = fields.Char(string="I index")
    of_season_efficiency = fields.Char(string="% Seasonal energy efficiency")
    of_fonds_air_bois = fields.Boolean(string="Eligible for Fonds Air Bois ?")
