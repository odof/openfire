# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, tools
from odoo.release import version_info


class PublisherWarrantyContract(models.AbstractModel):
    _inherit = "publisher_warranty.contract"

    def update_notification(self, cron_mode=True):
        """/!\\ CARE: For dev/preproduction/test servers only. /!\\

        Add the ability to disable the update notifier code.
        This parameter "disable_publisher_warranty_contract_notification" SHOULD NEVER BE SET IN A
        PRODUCTION ENVIRONNEMENT.

        THIS IS NOT LEGAL to disable the update notification in Odoo Enterpise Edition.
        Please read : https://www.odoo.com/documentation/master/legal/terms/enterprise.html#customer-obligations
        """
        return (
            True
            if tools.config.get("of_disable_publisher_warranty_contract_notification") and version_info[5] != "e"
            else super().update_notification(cron_mode)
        )
