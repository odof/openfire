# -*- coding: utf-8 -*-
from odoo.report import report_sxw
import time
import datetime


class sav(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(sav, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'get_company_name': self.get_company_name,
            'get_client_info': self.get_client_info,
            'get_priority': self.get_priority,
            'get_client_tel': self.get_client_tel,
            'maintenant': self.maintenant,
            'datetime': datetime,
            'get_objects': self.get_objects,
        })

    def get_objects(self, objects):
        if objects._name == 'of.planning.intervention':
            return [obj.sav_id for obj in objects if obj.sav_id]
        return objects

    def maintenant(self):
        return time.strftime('%Y-%m-%d')
    
    def get_company_name(self, o, user):
        if o.user_id:
            company = o.user_id.company_id.name
        else:
            company = user.company_id.name
        return company

    def get_client_info(self, address):
        address_all = ''
        if address.title.name:
            address_all += address.title.name + ' '
        if address.name:
            address_all += address.name + '\n'
        if address.street:
            if address_all != '':
                address_all += '\n' + address.street
            else:
                address_all += address.street
        if address.street2:
            if address_all != '':
                address_all += '\n' + address.street2
            else:
                address_all += address.street2
        if address.zip:
            if address_all != '':
                address_all += '\n' + address.zip
            else:
                address_all += address.zip
        if address.city:
            if address_all != '':
                address_all += ' ' + address.city
            else:
                address_all += address.city
        return address_all

    def get_priority(self, prio):
        priority = ''
        prio = int(prio)
        if prio == 0:
            priority = 'Basse'
        elif prio == 1:
            priority = 'Normale'
        elif prio == 2:
            priority = 'Haute'
        return priority

    def get_client_tel(self, address):
        tel = ''
        if address.mobile and (str(address.mobile) != ''):
            if tel != '':
                tel += ', ' + address.mobile
            else:
                tel += address.mobile
        if address.phone and (str(address.phone) != ''):
            if tel != '':
                tel += ', ' + address.phone
            else:
                tel += address.phone
        if address.fax and (str(address.fax) != ''):
            if tel != '':
                tel += ', ' + address.fax + ' (fax)'
            else:
                tel += address.fax + ' (fax)'
        return tel


report_sxw.report_sxw('report.of_project_issue.sav', 'project.issue', 'addons/of_project_issue/report/sav.rml', parser=sav, header=False)
report_sxw.report_sxw('report.of_project_issue.sav_planning', 'of.planning.intervention', 'addons/of_project_issue/report/sav.rml', parser=sav, header=False)
