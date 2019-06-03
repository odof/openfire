# -*- encoding: utf-8 -*-

import time
from odoo.report import report_sxw

class Courrier(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(Courrier, self).__init__(cr, uid, name, context)

        self.localcontext.update({
            'time': time,
            'setCompany': self.setCompany,
            'adr_get': self.adr_get,
        })

    # update company
    def setCompany(self, company):
        self.company = company
        self.localcontext['company'] = company
        self.rml_header = company.rml_header
        self.rml_header2 = company.rml_header2
        self.localcontext['logo'] = company.logo
        self.logo = company.logo

    # get client's company address
    def adr_get(self, partner):
        partner_obj = self.env['res.partner']
        partner = partner_obj.browse(partner.id)
        result = partner.read()[0]
        if result['title']:
            result['title'] = partner.title and partner.title.shortcut or False
        else:
            result['title'] = False
        return [result]

report_sxw.report_sxw('report.of_gesdoc.courriers', 'res.partner', "addons/of_gesdoc/report/courrier.rml", parser=Courrier, header=True)
report_sxw.report_sxw('report.of_gesdoc.courriers_se', 'res.partner', "addons/of_gesdoc/report/courrier_se.rml", parser=Courrier, header=True)
report_sxw.report_sxw('report.of_gesdoc.courriers_sehead', 'res.partner', "addons/of_gesdoc/report/courrier_sehead.rml", parser=Courrier, header=False)
report_sxw.report_sxw('report.of_gesdoc.courriers_se_sehead', 'res.partner', "addons/of_gesdoc/report/courrier_se.rml", parser=Courrier, header=False)
