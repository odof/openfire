# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class OFServiceRequestCreateInterventionWizard(models.TransientModel):
    _inherit = 'of.service.request.create.intervention.wizard'

    def _get_create_intervention_values(self, request):
        vals = super()._get_create_intervention_values(request)
        vals.update({'of_use_equipment': request.use_equipment})
        return vals
