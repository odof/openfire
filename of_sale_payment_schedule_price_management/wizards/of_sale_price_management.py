# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class OFPriceManagementWizard(models.TransientModel):
    _inherit = "of.sale.price.management.wizard"

    def compute(self, dry_run=False):
        """
        Calcule les nouveaux prix des articles sélectionnés en fonction de la méthode de calcul choisie.
        """
        super().compute(dry_run=dry_run)
        # Updates the payment schedule
        self.order_id.write({"of_payment_schedule_ids": self.order_id._of_compute_payment_schedule()})
