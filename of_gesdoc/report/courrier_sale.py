# -*- encoding: utf-8 -*-

import time
from openerp.report import report_sxw

class courrier_sale(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(courrier_sale, self).__init__(cr, uid, name, context)

        self.localcontext.update({
            'time': time,
            'setCompany': self.setCompany,
            'setAddress': self.set_address,
        })

    #update company
    def setCompany(self, company):
        self.company = company
        self.localcontext['company'] = company
        self.rml_header = company.rml_header
        self.rml_header2 = company.rml_header2
        self.localcontext['logo'] = company.logo
        self.logo = company.logo

    #get client's company address
    def set_address(self, order):
        partner = order.partner_id
        self.localcontext['addr'] = partner.child_ids and partner.child_ids[0] or partner

report_sxw.report_sxw('report.of_gesdoc.courriers_sale', 'sale.order', "addons/of_gesdoc/report/courrier_sale.rml", parser=courrier_sale, header=True)
report_sxw.report_sxw('report.of_gesdoc.courriers_sale_se', 'sale.order', "addons/of_gesdoc/report/courrier_sale_se.rml", parser=courrier_sale, header=True)
report_sxw.report_sxw('report.of_gesdoc.courriers_sale_sehead', 'sale.order', "addons/of_gesdoc/report/courrier_sale_sehead.rml", parser=courrier_sale, header=False)
report_sxw.report_sxw('report.of_gesdoc.courriers_sale_se_sehead', 'sale.order', "addons/of_gesdoc/report/courrier_sale_se.rml", parser=courrier_sale, header=False)

