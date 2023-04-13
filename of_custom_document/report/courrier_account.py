# -*- encoding: utf-8 -*-

import time
from odoo.report import report_sxw

class CourrierAccount(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(CourrierAccount, self).__init__(cr, uid, name, context)

        self.localcontext.update({
            'time': time,
            'setCompany': self.setCompany,
        })

    # update company
    def setCompany(self, company):
        self.company = company
        self.localcontext['company'] = company
        self.rml_header = company.rml_header
        self.rml_header2 = company.rml_header2
        self.localcontext['logo'] = company.logo
        self.logo = company.logo

report_sxw.report_sxw('report.of_gesdoc.courriers_account', 'account.invoice', "addons/of_gesdoc/report/courrier_account.rml", parser=CourrierAccount, header=True)
report_sxw.report_sxw('report.of_gesdoc.courriers_account_se', 'account.invoice', "addons/of_gesdoc/report/courrier_account_se.rml", parser=CourrierAccount, header=True)
report_sxw.report_sxw('report.of_gesdoc.courriers_account_sehead', 'account.invoice', "addons/of_gesdoc/report/courrier_account_sehead.rml", parser=CourrierAccount, header=False)
report_sxw.report_sxw('report.of_gesdoc.courriers_account_se_sehead', 'account.invoice', "addons/of_gesdoc/report/courrier_account_se.rml", parser=CourrierAccount, header=False)
