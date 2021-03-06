# -*- coding: utf-8 -*-

from odoo import models, fields, api
import re


def remove_html_balise(text):
    regex_remove = re.compile("<.*?>")  # permet de chercher toute chaine de charactère commançant par '<' et se terminant par '>'
    regex_replace = re.compile("</p>|</br>|</li>")  # liste des expression a remplacer par '\n'
    text = text.replace('\n', '').replace('\r', '')  # on enlève tout les retours à la ligne
    text = regex_replace.sub('\n', text)
    text = regex_remove.sub('', text)
    return text


class OfComposeMail(models.TransientModel):
    _inherit = 'of.compose.mail'

    @api.model
    def _get_objects(self, o):
        result = super(OfComposeMail, self)._get_objects(o)
        if o._name == 'of.planning.intervention':
            result.update({
                'interventions': o,
                'partner'      : o.partner_id,
                'address'      : o.address_id,
                'address_pose' : o.address_id,
                'shop'         : o.company_id,
                # order_id et invoice_id ne seront définis que dans of_sales,
                # mais getattr gère l'exception si le module n'est pas installé
                'order'        : getattr(o, 'order_id', self.env['sale.order']),
                'invoice'      : getattr(o, 'invoice_id', self.env['account.invoice']),
            })
        elif o._name == 'res.partner':
            result['interventions'] = o.intervention_partner_ids
        else:
            result['interventions'] = getattr(o, 'intervention_ids', self.env['of.planning.intervention'])
        return result

    @api.model
    def _get_dict_values(self, o, objects):
        fisc_position_obj = self.env['account.fiscal.position']
        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')
        result = super(OfComposeMail, self)._get_dict_values(o, objects)

        employees = []
        dates = []

        for intervention in objects['interventions']:
            for employee in intervention.employee_ids:
                if employee.name not in employees:
                    employees.append(employee.name)
            date_interv_da = fields.Datetime.from_string(intervention.date)
            date_interv_da = fields.Datetime.context_timestamp(self, date_interv_da)

            # La fonction date.strftime ne gère pas correctement les chaînes unicode, on ne peut donc pas faire strftime(u"%d/%m/%Y à %H:%M")
            dates.append(date_interv_da.strftime("%d/%m/%Y à %H:%M").decode('utf-8'))

        tache_product_ttc = ''
        duree = ''
        intervention = objects['interventions']
        if intervention:
            intervention = intervention[0]
            h = int(intervention.duree)
            m = 60 * (intervention.duree - h)
            duree = "%02d:%02d" % (h, m)

            if intervention.tache_id.product_id:
                tache_product_ht = intervention.tache_id.product_id.list_price or 0.0
                fpos = False
                partner = objects['partner']
                if partner:
                    fpos = self.env['account.fiscal.position'].get_fiscal_position(partner.id, delivery_id=intervention.address_id.id)
                if fpos:
                    tache_product_tax = 0.0
                    fpos = fisc_position_obj.browse(fpos)
                    for tax in fpos.tax_ids:
                        tache_product_tax += tax.tax_src_id.amount

                    lang_obj = self.env['res.lang']
                    lang_code = self._context.get('lang', partner.lang)
                    lang = lang_obj.search([('code', '=', lang_code)], limit=1)
                    tache_product_ttc = lang.format("%.2f", round(tache_product_ht * (1.0 + tache_product_tax), 2), grouping=True)

        result.update({
            'date_intervention': dates and dates[0] or '',
            'date_intervention_date': dates and dates[0].split()[0] or '',
            'date_intervention_heure': dates and dates[0].split()[2] or '',
            'employee': employees and employees[0] or '',
            'employees': "\n".join(employees),
            'dates_intervention': "\n".join(dates),
            'duree_intervention': duree,
            'tache': intervention and intervention.tache_id and intervention.tache_id.name or '',
            'tache_product_ttc': tache_product_ttc,
            'interv_description': intervention and intervention.description and remove_html_balise(intervention.description)
        })
        # Pour rétrocompatibilité
        result.update({
            'date_pose': result['date_intervention'],
            'date_pose_date': result['date_intervention_date'],
            'employee_pose': result['employee'],
            'employee_poses': result['employees'],
            'date_poses': result['dates_intervention'],
            'duree_pose': result['duree_intervention'],
            'tache_pose': result['tache'],
            'tache_product_ttc': tache_product_ttc,
        })
        return result

    def _get_model_action_dict(self):
        result = super(OfComposeMail, self)._get_model_action_dict()
        result['of.planning.pose'] = 'of_planning.courriers_pose'
        return result
