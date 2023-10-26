# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def _update_mail_activity_short_name(cr):
    """
    Init the new field 'of_short_name' for the existing activities and set the column as "not null"
    """
    cr.execute("UPDATE mail_activity_type SET of_short_name = name WHERE of_short_name IS NULL")
    # Cause of existing data in table we have to apply the constraint manually
    cr.execute("ALTER TABLE mail_activity_type ALTER of_short_name SET NOT NULL;")


def _transfer_leads_tags_to_partners(cr):
    """
    As tags are now linked to partners (we changed that) we need to update the tags of the partner linked to the lead.
    """
    # Create new tmp column to store old tag id
    cr.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'res_partner_category' "
        "AND column_name = 'old_tag_id';"
    )
    test_column = cr.fetchone()
    if not test_column:
        cr.execute("ALTER TABLE res_partner_category ADD COLUMN old_tag_id INTEGER;")

    # Create new categories for tags
    cr.execute(
        "INSERT INTO res_partner_category(name, color, active, create_uid, create_date, write_uid, "
        "write_date, old_tag_id) "
        "SELECT DISTINCT CT.name, CT.color, TRUE, 1, NOW(), 1, NOW(), CT.id "
        "FROM crm_tag CT "
        "WHERE CT.name NOT IN (SELECT name FROM res_partner_category) "
        "ON CONFLICT DO NOTHING;"
    )

    # Update tags for partners
    cr.execute(
        "INSERT INTO res_partner_res_partner_category_rel (partner_id, category_id) "
        "SELECT CL.partner_id as partner_id, RPC.id as category_id "
        "FROM crm_lead AS CL "
        "JOIN crm_tag_rel AS CTR ON CTR.lead_id = CL.id "
        "JOIN res_partner_category AS RPC ON RPC.old_tag_id = CTR.tag_id "
        "ON CONFLICT DO NOTHING"
    )

    # Remove tmp column
    cr.execute("ALTER TABLE res_partner_category DROP COLUMN old_tag_id")


def _create_partners_from_leads_without_partners(cr, env):
    """Create partners from leads without partners then assign them to the leads."""
    lead_obj = env['crm.lead']
    partner_obj = env['res.partner']

    # get data for partners to create from leads
    cr.execute(
        "SELECT id, street, street2, zip, city, state_id, country_id, phone, mobile, email_from AS email, "
        "COALESCE(partner_name, name) AS name, company_id "
        "FROM crm_lead "
        "WHERE partner_id IS NULL"
    )
    partner_data_list = cr.dictfetchall()
    partners_to_create = []
    for partner_data in partner_data_list:
        tmp_data = partner_data.copy()
        tmp_data.pop('id')
        partners_to_create.append(tmp_data)
    # create partners in batch
    partners = partner_obj.create(partners_to_create)

    # assign partners to leads
    for partner, partner_data in zip(partners, partner_data_list):
        lead = lead_obj.browse(partner_data.pop('id'))
        lead.partner_id = partner


def post_init_hook(cr, registry):
    """Migrate data from old fields to new ones."""
    env = api.Environment(cr, SUPERUSER_ID, {})

    _update_mail_activity_short_name(cr)
    _transfer_leads_tags_to_partners(cr)
    _create_partners_from_leads_without_partners(cr, env)
