# -*- coding: utf-8 -*-

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import config


class OFYousignSetup(models.TransientModel):
    _name = "of.yousign.setup.wizard"

    @api.model
    def _default_message(self):
        if self._verify_setup():
            return "Tout est déjà configuré."
        return (
            "Vous allez générer les workspaces et webhooks manquants pour cette base."
        )

    @api.model
    def _default_name(self):
        return self.env.user.company_id.name

    @api.model
    def _default_is_already_setup(self):
        return self._verify_setup()

    name = fields.Char(
        string="Nom sur Yousign", required=True, default=lambda s: s._default_name()
    )
    message = fields.Text(string="Message", default=lambda s: s._default_message())
    is_already_setup = fields.Boolean(default=lambda s: s._default_is_already_setup())

    @api.model
    def _verify_setup(self):
        ir_config_parameter_obj = self.env["ir.config_parameter"]
        for environment in ("sandbox",):

            if not ir_config_parameter_obj.get_param(
                "yousign.%s.workspace.uuid" % environment, ""
            ):
                break
            if not ir_config_parameter_obj.get_param(
                "yousign.%s.webhook.uuid" % environment, ""
            ):
                break
        else:
            return True
        return False

    def button_setup(self):
        self.ensure_one()
        self._setup_yousign_workspaces()
        self._setup_yousign_webhooks()
        self.message = "Les workspaces et webhooks ont été générés."
        return True

    @api.model
    def yousign_init(self, environment):
        apikey = environment and config.get("of_yousign_apikey_" + environment)
        if not apikey or not environment:
            raise UserError(
                _(
                    "One of the Yousign config parameters is missing in the Odoo server config file."
                )
            )

        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer %s" % apikey,
            "Accept": "application/json",
        }
        yousign_v3 = {
            "prod": "https://api.yousign.app/v3",
            "sandbox": "https://api-sandbox.yousign.app/v3",
        }
        url_base = yousign_v3[environment]
        return (url_base, headers)

    def yousign_request(
        self,
        method,
        url,
        expected_status_code=201,
        json=None,
        return_raw=False,
        environment="sandbox",
    ):
        url_base, headers = self.yousign_init(environment)
        full_url = url_base + url
        res = requests.request(method, full_url, headers=headers, json=json)
        if res.status_code != expected_status_code:
            try:
                res_json = res.json()
            except Exception:
                res_json = {}
            raise UserError(
                _(
                    "The HTTP %s request on Yousign webservice %s returned status code %d whereas %d was expected. "
                    "Error message: %s (%s)."
                )
                % (
                    method,
                    full_url,
                    res.status_code,
                    expected_status_code,
                    res_json.get("title"),
                    res_json.get("detail", _("no detail")),
                )
            )
        if return_raw:
            return res
        res_json = res.json()
        return res_json

    # Création de workspaces

    def _setup_yousign_workspaces(self):
        ir_config_parameter_obj = self.env["ir.config_parameter"]
        workspace_url = "/workspaces"
        data = self._get_workspace_data()
        cr = self.env.cr
        for environnement in ("sandbox", ):
            # workspace existe déjà, on passe au suivant
            if ir_config_parameter_obj.get_param(
                "yousign.%s.workspace.uuid" % environnement, ""
            ):
                continue
            response = self.yousign_request(
                "POST", workspace_url, json=data, environment=environnement
            )
            ir_config_parameter_obj.set_param(
                "yousign.%s.workspace.uuid" % environnement, response.get("id")
            )
            # on commit car yousign_request peut faire une erreur, si c'est le cas on ne veut pas rollback la création
            # du paramètre
            cr.commit()

    def _get_workspace_data(self):
        return {"name": self.name}

    # Création de webhooks

    def _setup_yousign_webhooks(self):
        ir_config_parameter_obj = self.env["ir.config_parameter"]
        webhook_url = "/webhooks"
        webhook_data = self._get_webhook_data()
        sandbox_webhook_data = self._get_webhook_data(sandbox=True)
        cr = self.env.cr
        try:
            # for env, data in [("prod", webhook_data), ("sandbox", sandbox_webhook_data)]:
            for env, data in [("sandbox", sandbox_webhook_data)]:
                if not all(data["workspaces"]):
                    # workspace manquant, ne pas tenter de créer
                    continue
                if ir_config_parameter_obj.get_param(
                    "yousign.%s.webhook.uuid" % env, ""
                ):
                    continue
                # la création de webhook est toujours fait en prod, c'est le booléen sandbox qui décide si il est pour
                # l'env de sandbox
                response = self.yousign_request(
                    "POST", webhook_url, json=data, environment="prod"
                )
                self.env["ir.config_parameter"].set_param(
                    "yousign.%s.webhook.uuid" % env, response.get("id")
                )
                self.env["ir.config_parameter"].set_param(
                    "yousign.%s.webhook.secret" % env, response.get("secret_key")
                )
                # on ne veut pas créer plusieurs webhook d'un même type d'environnement
                cr.commit()
        except Exception as e:
            cr.rollback()
            self.message = str(e)

    def _get_webhook_data(self, sandbox=False):
        web_base_url = (
            self.env["ir.config_parameter"]
            .get_param("web.base.url", "")
            .replace("http://", "https://")
        )
        env = sandbox and "sandbox" or "prod"
        workspace_uuid = self.env["ir.config_parameter"].get_param(
            "yousign.%s.workspace.uuid" % env, ""
        )
        db_name = self.env.cr.dbname
        webhook_url = sandbox and "yousign_sandbox_webhook" or "yousign_webhook"
        return {
            "sandbox": sandbox,
            "auto_retry": True,
            "enabled": True,
            "subscribed_events": [
                "signature_request.declined",
                "signature_request.canceled",
                "signature_request.done",
                "signature_request.expired",
                "signature_request.deleted",
            ],
            "endpoint": "{base_url}/{webhook_url}".format(
                base_url=web_base_url, webhook_url=webhook_url
            ),
            "description": "webhook de la base {db_name}".format(db_name=db_name),
            "workspaces": [workspace_uuid],
            "scopes": ["*"],
        }
