# -*- coding: utf-8 -*-

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    datastore_crm = env["of.datastore.crm.receiver"].search([], limit=1)
    datastore_leads = env["crm.lead"].search([("of_datastore_lead", "!=", False)])
    if datastore_crm and datastore_leads:
        datastore_leads.write({"of_datastore_db_name": datastore_crm.db_name})
