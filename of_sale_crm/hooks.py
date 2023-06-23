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


def _update_of_customer_state_on_partners(env):
    """
    Update of_customer_state on partners.

    For no customer partners (customer = False): of_customer_state = 'other'
    For customer partners:
        if a partner (or its parent if any) has at least one sale or
            one invoice: of_customer_state = 'customer'
        else: of_customer_state = 'lead'
    We take care of children after taking care of their parent.
    """
    partner_obj = env['res.partner'].with_context(active_test=False)
    # all partners
    partners = partner_obj.search([])
    # init of_customer_state to 'other' for all partners
    partners.write({'of_customer_state': 'other'})

    # init of_customer_state for customers
    customers = partner_obj.search([('customer_rank', '>=', 1)])
    to_lead = env['res.partner']
    to_customer = env['res.partner']
    len_customers = len(customers)

    todo = partner_obj.search(
        [('customer_rank', '>=', 1), '|', ('parent_id', '=', False), ('parent_id.customer_rank', '>=', 1)]
    )
    while todo:
        partner = todo[0]
        todo -= partner
        if partner.sale_order_count == 0 and partner.total_invoiced == 0:
            if partner.parent_id and partner.parent_id in to_customer:
                to_customer += partner
            else:
                to_lead += partner
        else:
            to_customer += partner
        # potentially inactive children
        todo += partner_obj.search([('parent_id', '=', partner.id), ('customer', '=', True)])

    to_lead.write({'of_customer_state': 'lead'})
    to_customer.write({'of_customer_state': 'customer'})
    len_done = len(to_lead) + len(to_customer)

    if len_customers != len_done:  # not all partners have been processed
        _logger.warning(
            f"hook '_res_partner_post_install' inconsistency. Customers: {len_customers}, processed: {len_done}"
        )
    else:
        _logger.info(f"hook '_res_partner_post_install' done. {len_done} partners processed")


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
    _update_of_customer_state_on_partners(registry.env)
