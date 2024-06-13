# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    configure_codes_for_partners(env)


def configure_codes_for_partners(env):
    """
    This function is automatically called during model initialization. It configures the codes
    for customers and suppliers
    """
    company = env.user.company_id

    xml_obj = env['ir.model.data']
    sequence_obj = env['ir.sequence']

    vals = {}

    customer_seq = sequence_obj.browse(xml_obj.search([('name', 'like', 'sequence_customer_account')]).res_id)
    if customer_seq and customer_seq.active:
        code = "'%s%%0%si%s' %% partner.id" % (
            customer_seq.prefix or '',
            customer_seq.padding,
            customer_seq.suffix or '',
        )
        vals['of_customer_code'] = (code, 'partner.name')
        customer_seq.active = False

    supplier_seq = sequence_obj.browse(xml_obj.search([('name', 'like', 'sequence_supplier_account')]).res_id)
    if supplier_seq and supplier_seq.active:
        code = "'%s%%0%si%s' %% partner.id" % (
            supplier_seq.prefix or '',
            supplier_seq.padding,
            supplier_seq.suffix or '',
        )
        vals['of_supplier_code'] = (code, 'partner.name')
        supplier_seq.active = False

    company.write(vals)
