# -*- encoding: utf-8 -*-

import time
from openerp.report import report_sxw

class courrier_crm(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(courrier_crm, self).__init__(cr, uid, name, context)

        self.localcontext.update({
            'time': time,
            'setCompany': self.setCompany,
            'adr_get': self.adr_get,
        })

    #update company
    def setCompany(self, company):
        self.company = company
        self.localcontext['company'] = company
        self.rml_header = company.rml_header
        self.rml_header2 = company.rml_header2
        self.localcontext['logo'] = company.logo
        self.logo = company.logo

    #get client's address
    def adr_get(self, partner):
        pad_obj = self.pool.get('res.partner.address')
        crm_obj = self.pool.get('crm.lead')
        if partner.contact_name:
            result = crm_obj.read(self.cr, self.uid, [partner.id])
        elif partner.partner_address_id:
            result = pad_obj.read(self.cr, self.uid, [partner.partner_address_id.id])
        elif partner.partner_id:
            c_ids = pad_obj.search(self.cr, self.uid, [('partner_id', '=', partner.partner_id.id)])
            result = pad_obj.read(self.cr, self.uid, [c_ids[0]])
        else:
            c_ids[0] = 0
            result = pad_obj.read(self.cr, self.uid, [c_ids[0]])

        if result:
            if result[0]['title']:
                pad = pad_obj.browse(self.cr, self.uid, c_ids[0])
                result[0]['title'] = pad.title and pad.title.shortcut or False
            else:
                result[0]['title'] = False
        else:
            result[0]['title'] = False
            result[0]['name'] = ''
            result[0]['street'] = ''
            result[0]['street2'] = ''
            result[0]['zip'] = ''
            result[0]['city'] = ''
        return [result[0]]

report_sxw.report_sxw('report.of_gesdoc.courriers_crm', 'crm.lead', "addons/of_gesdoc/report/courrier_crm.rml", parser=courrier_crm, header=True)
report_sxw.report_sxw('report.of_gesdoc.courriers_crm_se', 'crm.lead', "addons/of_gesdoc/report/courrier_crm_se.rml", parser=courrier_crm, header=True)
report_sxw.report_sxw('report.of_gesdoc.courriers_crm_sehead', 'crm.lead', "addons/of_gesdoc/report/courrier_crm.rml", parser=courrier_crm, header=False)
report_sxw.report_sxw('report.of_gesdoc.courriers_crm_se_sehead', 'crm.lead', "addons/of_gesdoc/report/courrier_crm_se.rml", parser=courrier_crm, header=False)

