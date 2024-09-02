# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import models

logger = logging.getLogger(__name__)


class ESBService(models.Model):
    _inherit = 'of.esb.service'

    def get_data_email(self, args):
        logger.info(f"get_data_email : {args}")
        return []

    def set_data_email(self, args):
        logger.info(f"set_data_email : {args}")
        return True
