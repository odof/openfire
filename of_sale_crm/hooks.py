# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def _account_invoice_post_install(cr):
    cr.execute(
        "UPDATE account_move AM "
        "SET of_canvasser_id = COALESCE(SO.of_canvasser_id, RP.of_canvasser_id) "
        "FROM account_move AM2 "
        "INNER JOIN res_partner RP ON RP.id = AM2.partner_id "
        "LEFT JOIN account_move_line AML ON (AML.move_id = AM2.id) "
        "LEFT JOIN sale_order_line_invoice_rel SOLIR ON (SOLIR.invoice_line_id = AML.id)"
        "LEFT JOIN sale_order_line SOL ON (SOL.id = SOLIR.order_line_id) "
        "LEFT JOIN sale_order SO ON (SO.id = SOL.order_id) "
        "WHERE AM.id = AM2.id"
    )


def _sale_order_post_install(cr):
    """
    À l'installation du module :
        - les commandes avec l'ancien état 'Devis' sont passés au nouvel état 'Devis'
        - le nouveau champ 'Devis envoyé' est passé à vrai pour les commandes avec l'ancien état 'Devis envoyé'
    """
    # :todo: Prévoir un script inverse à la désinstallation du module
    cr.execute("UPDATE sale_order SET of_sent_quotation = True WHERE state = 'sent'")
    cr.execute("UPDATE sale_order SET state = 'sent' WHERE state = 'draft'")
    cr.execute(
        "UPDATE sale_order SO "
        "SET of_canvasser_id = COALESCE(CL.of_canvasser_id, RP.of_canvasser_id) "
        "FROM sale_order SO2 "
        "INNER JOIN res_partner RP ON RP.id = SO2.partner_id "
        "LEFT JOIN crm_lead CL ON (CL.id = SO2.opportunity_id) "
        "WHERE SO.id = SO2.id"
    )


def _set_default_order_start_state(env):
    settings = env["res.config.settings"].create({})
    settings.of_sale_order_start_state = "quotation"
    settings.execute()


def post_init_hook(cr, registry):
    """Migrate data from old fields to new ones."""

    env = api.Environment(cr, SUPERUSER_ID, {})
    _account_invoice_post_install(cr)
    _sale_order_post_install(cr)
    _set_default_order_start_state(env)
