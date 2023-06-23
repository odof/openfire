# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

_logger = logging.getLogger(__name__)


def _account_invoice_post_install(cr):
    cr.execute(
        "UPDATE account_invoice AI "
        "SET of_canvasser_id = COALESCE(SO.of_canvasser_id, RP.of_prospecteur_id) "
        "FROM account_invoice AI2 "
        "INNER JOIN res_partner RP ON RP.id = AI2.partner_id "
        "LEFT JOIN sale_order SO ON (SO.name = AI2.origin) "
        "WHERE AI.id = AI2.id"
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


def post_init_hook(cr, registry):
    """Migrate data from old fields to new ones."""

    _account_invoice_post_install(cr)
    _sale_order_post_install(cr)
