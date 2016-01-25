# -*- coding: utf-8 -*-

from openerp.osv import fields, osv

class crm_lead(osv.osv):
    _inherit = 'crm.lead'

    _columns = {
        'website': fields.char('Website', help="Website of Lead"),
    }

    def on_change_partner_id(self, cr, uid, ids, partner_id, context=None):
        res = super(crm_lead,self).on_change_partner_id(cr, uid, ids, partner_id, context=context)
        if partner_id:
            partner = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
            res['value']['website'] = partner.website
        return res

    def _lead_create_contact(self, cr, uid, lead, name, is_company, parent_id=False, context=None):
        partner_obj = self.pool.get('res.partner')
        partner_id = super(crm_lead,self)._lead_create_contact(cr, uid, lead, name, is_company, parent_id=parent_id, context=context)
        if lead.website:
            partner_obj.write(cr, uid, partner_id, {'website': lead.website}, context=context)
        return partner_id
