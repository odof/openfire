# -*- coding: utf-8 -*-

from odoo import api, fields, models


class YousignDirectSignatureWizard(models.TransientModel):
    _name = 'of.yousign.direct.signature.wizard'

    model = fields.Char(string='Related Document Model', readonly=True)
    res_id = fields.Integer(string='Related Document ID', readonly=True)
    request_id = fields.Many2one(comodel_name='of.yousign.request', string=u"Requête")
    signatory_id = fields.Many2one(comodel_name='of.yousign.request.signatory', string="Signataire")
    iframe = fields.Html(string="iFrame", readonly=True, sanitize=False)

    @api.depends('signatory_id')
    def _set_iframe(self):
        ir_config_param_obj = self.env["ir.config_parameter"].sudo()
        environment = environment = (
            ir_config_param_obj.get_param("of.yousign.connector.yousign_environment")
            or "sandbox"
        )
        if self.signatory_id and self.signatory_id.signature_link:
            signature_link = self.signatory_id.signature_link
            if environment == 'sandbox':
                signature_link += '&disable_domain_validation=true'
            iframe_text = '<iframe src="{link}" width="800" height="1080"/>'.format(link=signature_link)
            self.iframe = iframe_text
        return True

    def validate(self):
        # self.request_id.update_status()
        # if self.request_id.state == 'signed':
        #     self.request_id.archive()
        return True
