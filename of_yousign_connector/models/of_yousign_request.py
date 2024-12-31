# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import codecs
import logging
import os
import re
import tempfile
from base64 import b64decode, b64encode
from contextlib import closing
from io import StringIO

from PyPDF2 import PdfFileReader

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import config

from odoo.addons.of_base.models.res_partner import convert_phone_number

logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:
    logger.debug("Cannot import requests")
try:
    from PyPDF2.errors import PdfReadError
except ImportError:
    from PyPDF2.utils import PdfReadError


def rank2position_builder(width, height, x, y, mention=""):
    base = {
        "width": width,
        "height": height,
        "x": x,
        "y": y,
    }
    if mention:
        base.update(
            {
                "type": "mention",
                "mention": mention,
            }
        )
    else:
        base.update(
            {
                "type": "signature",
            }
        )
    return base


class OFYousignRequest(models.Model):
    _name = "of.yousign.request"
    _description = "YouSign Request"
    _order = "id desc"
    _inherit = ["mail.thread"]

    @api.model
    def default_get(self, fields_list):
        res = super(OFYousignRequest, self).default_get(fields_list)
        yousign_request_template_obj = self.env["of.yousign.request.template"]
        model = self._context.get("active_model")
        res_id = self._context.get("active_id")
        if not model or not res_id:
            logger.debug(
                "No active_model or no active_id in context, so no "
                "no generation from yousign request template"
            )
            return res
        if model == self._name:
            return res
        template = False
        templates = False
        if res.get("company_id"):
            templates = yousign_request_template_obj.search(
                [("model", "=", model), ("company_id", "=", res.get("company_id"))]
            )
        if not templates:
            templates = yousign_request_template_obj.search([("model", "=", model)])
        if templates:
            template = templates[0]
        # print "model=%s, res_id=%s" % (model, res_id)
        if template and model != template.model:
            raise UserError(
                _("Wrong active_model (%s should be %s)")
                % (self._context.get("active_model"), template.model)
            )
        source_obj = self.env[model].browse(int(res_id))
        res.update(
            {
                "name": source_obj.display_name,
                "model": model,
                "res_id": res_id,
                "template_id": template and template.id,
            }
        )
        return res

    @api.model
    def _lang_get(self):
        langs = self.env["res.lang"].search([])
        return [(lang.code, lang.name) for lang in langs]

    name = fields.Char()
    res_name = fields.Char(
        compute="_compute_res_name",
        string="Related Document Name",
        store=True,
        readonly=True,
    )
    model = fields.Char(
        string="Related Document Model",
        select=True,
        readonly=True,
        track_visibility="onchange",
    )
    res_id = fields.Integer(
        string="Related Document ID",
        select=True,
        readonly=True,
        track_visibility="onchange",
    )
    ordered = fields.Boolean(string="Sign one after the other")
    language = fields.Selection(
        selection=lambda s: s._lang_get(),
        string="Language",
        readonly=True,
        states={"draft": [("readonly", False)]},
        track_visibility="onchange",
    )
    attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        string="Documents to Sign",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    signed_attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="Signed Documents",
        readonly=True,
    )
    signed_attachment_datas = fields.Binary(
        related="signed_attachment_id.datas", readonly=True
    )
    signed_attachment_name = fields.Char(
        related="signed_attachment_id.name", readonly=True
    )
    signatory_ids = fields.One2many(
        comodel_name="of.yousign.request.signatory",
        inverse_name="request_id",
        string="Signatories",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("sent", "Sent"),
            ("signed", "Signed"),
            ("error", "Error"),
            ("archived", "Archived"),
            ("cancel", "Cancelled"),
        ],
        default="draft",
        readonly=True,
        track_visibility="onchange",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        ondelete="cascade",
        readonly=True,
        states={"draft": [("readonly", False)]},
        track_visibility="onchange",
        default=lambda self: self.env["res.company"]._company_default_get("of.yousign.request"),
    )
    ys_identifier = fields.Char(
        string="YouSign ID", readonly=True, track_visibility="onchange"
    )
    last_status_update = fields.Datetime(string="Last Status Update", readonly=True)
    has_automatic_reminder = fields.Boolean(
        string="Automatic Reminder",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    remind_mail_subject = fields.Char(
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    remind_mail_body = fields.Html(
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    remind_interval = fields.Integer(
        default=3,
        readonly=True,
        states={"draft": [("readonly", False)]},
        help="Number of days between 2 auto-reminders by email.",
    )
    remind_limit = fields.Integer(
        default=10,
        readonly=True,
        states={
            "draft": [("readonly", False)],
        },
    )
    expiry_date = fields.Date()
    template_id = fields.Many2one(
        comodel_name="of.yousign.request.template",
        string="Template",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    # experience_id = fields.Many2one(
    #     comodel_name="of.yousign.experience", string="Experience"
    # )
    partner_ids = fields.Many2many(
        comodel_name="res.partner",
        relation="of_yousign_request_res_partner_rel",
        column1="request_id",
        column2="partner_id",
        string="Partners to notify",
        domain=[("email", "!=", False)],
    )

    @api.depends("model", "res_id")
    def _compute_res_name(self):
        for req in self:
            name = "None"
            if req.res_id and req.model:
                obj = self.env[req.model].browse(req.res_id)
                name = obj.display_name
            req.res_name = name

    @api.onchange("template_id")
    def _onchange_of_template_id(self):
        report_obj = self.env["ir.actions.report"].sudo().with_context(self._context)
        if template := self.model and self.res_id and self.template_id:
            model = self.model
            res_id = self.res_id
            ir_attachment_obj = self.env["ir.attachment"]
            source_obj = self.env[model].browse(res_id)
            # signatory_ids = []
            # for signatory in template.signatory_ids:
            #     signatory_vals = signatory.prepare_template2request(
            #         model, res_id)
            #     signatory_ids.append((0, 0, signatory_vals))
            attachment_ids = [(5, 0)]
            report_order = 0
            partners = template.partner_ids
            if template.creator:
                partners |= self.env.user.partner_id
            if template.report_ids:
                for report in template.report_ids:
                    report_data, report_extension = report_obj._render_qweb_pdf(
                        report_ref=report.report_name,
                        res_ids=[res_id],
                    )
                    order = report_order
                    report_order += 1
                    if not report_data:
                        continue
                    if source_obj.display_name:
                        tmp_filename = source_obj.display_name[:50]
                        tmp_filename = tmp_filename.replace(" ", "_")
                        full_filename = "%s.%s" % (tmp_filename, report_extension)
                    else:
                        full_filename = "document_to_sign.%s" % report_extension
                    attach_vals = {
                        "name": full_filename,
                        # 'res_id': Signature request is not created yet
                        "res_model": self._name,
                        "datas": b64encode(report_data),
                        "of_yousign_order": order,
                    }
                    attach = ir_attachment_obj.with_context(report_name=report.report_name).create(
                        attach_vals
                    )
                    attachment_ids.append((4, attach.id))
            self.update(template.prepare_template2request())
            self.update(
                {
                    "attachment_ids": attachment_ids,
                    "partner_ids": [(4, partner_id) for partner_id in partners._ids],
                }
            )

    def unlink(self):
        if any(request.state in ("sent", "signed", "archived") for request in self):
            raise UserError(
                _(
                    "Impossible to delete a request that has been sent, signed or archived"
                )
            )
        return super(OFYousignRequest, self).unlink()

    ############
    ## Flow
    ############

    def send(self):
        logger.info("Start to send YS request %s ID %d", self.name, self.id)
        if not self.signatory_ids:
            raise UserError(
                _("There are no signatories on request %s!") % self.display_name
            )
        if not self.attachment_ids:
            raise UserError(
                _("There are no documents to sign on request %s!") % self.display_name
            )
        # commentaire pour vérifier hook
        # if not self.init_mail_subject:
        #     raise UserError(
        #         _("Missing init mail subject on request %s.") % self.display_name
        #     )
        # if not self.init_mail_body:
        #     raise UserError(
        #         _("Missing init mail body on request %s.") % self.display_name
        #     )
        if self.state == "draft":
            if not self.ys_identifier:
                self._create_yousign_request()
            attach_data = self._create_yousign_request_documents()
            self._create_yousign_request_signers(attach_data)
            self._activate_yousign_request()
        return True

    ############
    ## Model functions
    ############

    @api.model
    def signature_position(self, signatory_rank):
        # llx,lly,urx,ury".
        # llx=left lower x coordinate,
        # lly=left lower y coordinate,
        # urx=upper right x coordinate,
        # ury = upper right y coordinate
        # correspondances entre v2 et v3 faites grâce à https://placeit.yousign.fr/
        rank2position = {
            1: rank2position_builder(width=245, height=70, x=40, y=190),
            2: rank2position_builder(width=245, height=70, x=315, y=190),
            3: rank2position_builder(width=245, height=70, x=40, y=330),
            4: rank2position_builder(width=245, height=70, x=315, y=330),
        }
        default_position = rank2position_builder(width=240, height=72, x=56, y=378)
        if signatory_rank not in rank2position:
            logger.warning(
                "Requesting signature position for undeclared signatory_rank %d",
                signatory_rank,
            )
        return rank2position.get(signatory_rank, default_position)

    @api.model
    def mention_position(self, signatory_rank, top=True, mention=""):
        if not mention:
            return False
        if top:
            rank2position = {
                1: rank2position_builder(
                    width=245, height=24, x=40, y=166, mention=mention
                ),
                2: rank2position_builder(
                    width=245, height=24, x=315, y=166, mention=mention
                ),
                3: rank2position_builder(
                    width=245, height=24, x=40, y=310, mention=mention
                ),
                4: rank2position_builder(
                    width=245, height=24, x=315, y=310, mention=mention
                ),
            }
            default_position = rank2position_builder(
                width=240, height=24, x=56, y=354, mention=mention
            )
        else:
            rank2position = {
                1: rank2position_builder(
                    width=245, height=24, x=40, y=242, mention=mention
                ),
                2: rank2position_builder(
                    width=245, height=24, x=315, y=242, mention=mention
                ),
                3: rank2position_builder(
                    width=245, height=24, x=40, y=382, mention=mention
                ),
                4: rank2position_builder(
                    width=245, height=24, x=315, y=382, mention=mention
                ),
            }
            default_position = rank2position_builder(
                width=240, height=24, x=56, y=450, mention=mention
            )
        return rank2position.get(signatory_rank, default_position)

    @api.model
    def add_empty_page(self, attach):
        """
        Permet d'ajouter une page blanche a la suite du document
        :return: Document avec page blanche à la fin
        """
        # if attach.of_yousign_report:
        #     return attach.datas.decode("base64")

        filename = attach.name
        # attach_data_stream = StringIO(attach_data)
        decoded_pdf = b64decode(attach.datas)
        if attach.of_yousign_report:
            return decoded_pdf
        temp_data_file_fd, temp_data_file_path = tempfile.mkstemp(
            suffix=".pdf", prefix=f"{filename}-temp"
        )
        with closing(os.fdopen(temp_data_file_fd, "wb")) as temp_file:
            temp_file.write(decoded_pdf)
        original_pdf_stream = open(temp_data_file_path, "rb")
        report_obj = self.env["ir.actions.report"].sudo().with_context(self._context)
        try:
            pdf = PdfFileReader(original_pdf_stream)
        except PdfReadError as e:
            raise UserError(
                _(
                    "File to sign '%s' is not a valid PDF file. "
                    "You must convert it to PDF before including it in a YouSign request."
                )
                % filename
            )
        finally:
            os.remove(temp_data_file_path)
        num_pages = str(pdf.getNumPages())
        blank_page_data = report_obj.with_context(
            of_doc_name=filename, of_doc_page_nb=num_pages
        )._render_qweb_pdf(
            report_ref="of_yousign_connector.yousign_attachment_blank_page_report",
            res_ids=[attach.id],
        )[
            0
        ]

        temp_blank_file_fd, temp_blank_file_path = tempfile.mkstemp(
            suffix=".pdf", prefix="blank-page-temp"
        )
        with closing(os.fdopen(temp_blank_file_fd, "wb")) as temp_file:
            temp_file.write(blank_page_data)
        # TODO: need stream not documents, return stream not path
        blank_page_pdf_stream = open(temp_blank_file_path, "rb")
        try:
            original_pdf_stream.seek(0, 0)  # retourner au début
            result_file_stream = report_obj._merge_pdfs(
                [original_pdf_stream, blank_page_pdf_stream]
            )
            result_file_stream.seek(0, 0)
            data = result_file_stream.read()
        finally:
            os.remove(temp_blank_file_path)
        return data

    ############
    ## API related functions
    ############

    def yousign_init(self):
        self.ensure_one()
        ir_config_param_obj = self.env["ir.config_parameter"].sudo()
        environment = (
            ir_config_param_obj.get_param("of.yousign.connector.yousign_environment")
            or "sandbox"
        )
        apikey = environment and config.get("of_yousign_apikey_" + environment)
        if not apikey or not environment:
            raise UserError(
                _(
                    "One of the YouSign config parameters is missing in the Odoo server config file."
                )
            )
        headers = {
            "Authorization": "Bearer %s" % apikey,
            "Accept": "application/json",
        }
        yousign_v3 = {
            "prod": "https://api.yousign.app/v3",
            "sandbox": "https://api-sandbox.yousign.app/v3",
        }

        return (yousign_v3[environment], headers)

    def yousign_request(
        self,
        method,
        url,
        expected_status_code=201,
        json=None,
        return_raw=False,
        files=None,
    ):
        self.ensure_one()
        url_base, headers = self.yousign_init()
        full_url = url_base + url
        logger.info(
            "Sending %s request on %s. Expecting status code %d.",
            method,
            full_url,
            expected_status_code,
        )
        logger.debug("JSON data sent: %s", json)
        if files:
            res = requests.request(method, full_url, headers=headers, files=files)
        else:
            res = requests.request(method, full_url, headers=headers, json=json)
        if res.status_code != expected_status_code:
            logger.error("Status code received: %s.", res.status_code)
            try:
                res_json = res.json()
            except Exception:
                res_json = {}
            raise UserError(
                _(
                    "The HTTP %s request on YouSign webservice %s returned status "
                    "code %d whereas %d was expected. Error message: %s (%s)."
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
        logger.debug("JSON webservice answer: %s", res_json)
        return res_json

    def _create_yousign_request(self):
        """
        https://developers.yousign.com/reference/post-signature_requests
        fo exemple of content and response
        """
        self.ensure_one()
        if not self.company_id.of_yousign_external_id:
            raise ValidationError(
                "Cette société ne dispose pas d'identifiant externe YouSign."
            )
        ir_config_param_obj = self.env["ir.config_parameter"].sudo()
        environment = (
            ir_config_param_obj.get_param("of.yousign.connector.yousign_environment")
            or False
        )
        workspace_id = self.env["ir.config_parameter"].get_param(
            "yousign.%s.workspace.uuid" % environment, ""
        )
        if not workspace_id:
            raise ValidationError(
                "Il faut générer l'espace de travail avant de créer des demandes de signatures."
            )
        data = {
            "name": self.name,  # required : string
            "delivery_mode": "email",  # required : string; 'email' or 'none'
            "ordered_signers": True,  # boolean
            "external_id": self.company_id.of_yousign_external_id,  # mandatory : string
            "audit_trail_locale": "fr",  # string; 'de', 'en', 'es', 'fr', 'it'
            "email_notification": {
                "sender": {
                    "type": "custom",
                    "custom_name": self.company_id.name,
                }
            },
            "workspace_id": workspace_id,
        }
        # if self.of_experience_id:
        #     data["custom_experience_id"] = self.of_experience_id.experience_id
        if self.expiry_date:
            data["expiration_date"] = (self.expiry_date,)  # date; format yyyy-mm-dd
        if self.has_automatic_reminder:
            data["reminder_settings"] = {
                "interval_in_days": self.remind_interval,  # required : int; min 1
                "max_occurrences": self.remind_limit,  # required : int; 1 to 10
            }  # reminder_settings object
        json_response = self.yousign_request("POST", "/signature_requests", json=data)
        update_request = {
            "ys_identifier": json_response["id"],
        }
        if json_response.get("expiration_date"):
            update_request["expiry_date"] = fields.Date.from_string(
                json_response["expiration_date"]
            )
        self.write(update_request)
        self.env.cr.commit()
        return data

    def _create_yousign_request_documents(self, anchors=False):
        """
        https://developers.yousign.com/reference/post-signature_requests-signaturerequestid-documents
        fo exemple of content and response
        """
        self.ensure_one()
        attach_data = {}
        for attach in self.attachment_ids:
            if attach.of_ys_identifier:
                continue
            # We decide to always add signature on last page
            pdf_decoded = self.add_empty_page(attach)
            filename = attach.name  # TODO: vérifier champ a utiliser
            # TODO: vérifier les libs utilisées
            temp_file_fd, temp_file_path = tempfile.mkstemp(
                suffix=".pdf", prefix=f"{filename}-temp"
            )
            with closing(os.fdopen(temp_file_fd, "wb")) as temp_file:
                temp_file.write(pdf_decoded)
            pdf_file = open(temp_file_path, "rb")
            try:
                pdf = PdfFileReader(pdf_file)
            except PdfReadError:
                raise UserError(
                    _(
                        "File to sign '%s' is not a valid PDF file. "
                        "You must convert it to PDF before including it in a YouSign request."
                    )
                    % filename
                )
            num_pages = pdf.getNumPages()
            logger.info("PDF %s has %d pages", filename, num_pages)
            attach_data[attach] = {
                "filename": filename,
                "num_pages": num_pages,
                "id": attach.of_ys_identifier,
                "file_path": temp_file_path,
                "buffer": pdf_file,
            }
            pdf_file.seek(0, 0)
        attach_url = f"/signature_requests/{self.ys_identifier}/documents"
        for attach, attach_vals in sorted(
            attach_data.items(), key=lambda item: item[0].of_yousign_order
        ):
            if attach.of_ys_identifier:
                continue
            data = {
                "file": (
                    attach_vals["filename"],
                    attach_vals["buffer"],
                    attach.mimetype,
                ),
                "nature": (
                    None,
                    "signable_document",
                ),  # required: string; 'attachment', 'signable_document'
            }
            if anchors:
                data["parse_anchors"] = (None, "true")
            json_response = self.yousign_request("POST", attach_url, files=data)
            attach_vals["id"] = json_response["id"]
            attach_vals["all_data"] = json_response
            attach.write({"of_ys_identifier": json_response["id"]})
            self.env.cr.commit()
            # ne retirer que les fichiers temporaires
            if attach_vals["file_path"].startswith("/tmp/"):
                os.remove(attach_vals["file_path"])
        return attach_data

    def _create_yousign_request_signers(self, attachments={}):
        """
        https://developers.yousign.com/reference/post-signature_requests-signaturerequestid-signers
        fo exemple of content and response
        """
        self.ensure_one()
        signatory_rank = 0
        signer_url = f"/signature_requests/{self.ys_identifier}/signers"
        for signat in self.signatory_ids:
            if signat.ys_identifier:
                continue
            if not signat.lastname:
                raise UserError(
                    _("Missing lastname on one of the signatories of request %s")
                    % self.display_name
                )
            if not signat.firstname:
                raise UserError(
                    _("Missing firstname on signatory '%s'" % signat.lastname)
                )
            if not signat.email:
                raise UserError(
                    _("Missing email on the signatory '%s'") % signat.lastname
                )
            mobile = convert_phone_number(
                signat.mobile, default_country_code="FR", strict=True
            )
            if not mobile:
                raise UserError(
                    _("Missing mobile phone number on signatory '%s'.")
                    % signat.lastname
                )
            signatory_rank += 1
            info = {
                "first_name": signat.firstname,  # required: string
                "last_name": signat.lastname,  # required: string
                "email": signat.email.strip(),  # required: string
                "phone_number": mobile,  # required if signature_authentication_mode == 'otp_sms': string; E.164 format
                "locale": "fr",  # required : string; 'en', 'fr', 'de', 'it', 'nl', 'es', 'pl'
            }
            signatory_fields = []
            base_signature_field = self.signature_position(signatory_rank)
            top_mention = self.mention_position(
                signatory_rank, mention=signat.top_mention
            )
            bottom_mention = self.mention_position(
                signatory_rank, top=False, mention=signat.bottom_mention
            )
            for x, attach_vals in sorted(
                attachments.items(), key=lambda item: item[0].of_yousign_order
            ):
                copy_signature_field = base_signature_field.copy()
                page_dict = {
                    "document_id": attach_vals["id"],
                    "page": attach_vals["num_pages"],
                }
                copy_signature_field.update(page_dict)
                signatory_fields.append(copy_signature_field)
                if top_mention:
                    top_mention_copy = top_mention.copy()
                    top_mention_copy.update(page_dict)
                    signatory_fields.append(top_mention_copy)
                if bottom_mention:
                    bottom_mention_copy = bottom_mention.copy()
                    bottom_mention_copy.update(page_dict)
                    signatory_fields.append(bottom_mention_copy)
            signatory_data = {
                "info": info,  # required: info object
                "fields": signatory_fields,  # list of field objects
                "signature_level": "electronic_signature",  # required : string
                # string; 'otp_email', 'otp_sms', 'no_otp'
                "signature_authentication_mode": signat.auth_mode == "sms"
                and "otp_sms"
                or "otp_email",
                # option is disabled by default
            }
            json_response = self.yousign_request(
                "POST", signer_url, json=signatory_data
            )
            record_data = {"ys_identifier": json_response["id"]}
            signat.write(record_data)
            self.env.cr.commit()

    def _activate_yousign_request(self):
        self.ensure_one()
        if self.state != "draft":
            return False
        activate_url = f"/signature_requests/{self.ys_identifier}/activate"
        json_response = {}
        # json_response = self.yousign_request("POST", activate_url, json={})
        # get_url = f"/signature_requests/{self.ys_identifier}/signers/{self.signatory_ids.ys_identifier}"
        # json_response = self.yousign_request("GET", get_url, json={}, expected_status_code=200)
        # self.signatory_ids.write({"state": "pending","signature_link": json_response.get("signature_link") })
        if json_response.get("status", "") == "ongoing":
            self.write({"state": "sent"})
        for signer in json_response.get("signers"):
            signatory = self.signatory_ids.filtered(
                lambda r: r.ys_identifier == signer.get("id")
            )
            if signatory and signer.get("status", "") == "initiated":
                signatory.write(
                    {
                        "state": "pending",
                        "signature_link": signer.get("signature_link"),
                        # "signature_link_expiration": signer.get(
                        #     "signature_link_expiration_date"
                        # ),
                    }
                )
        return True

    def archive(self):
        self.ensure_one()
        download_url = (
            "/signature_requests/{signatureRequestId}/documents/download".format(
                signatureRequestId=self.ys_identifier
            )
        )
        url_base, headers = self.yousign_init()
        full_url = url_base + download_url
        headers.update({"accept": "application/zip, application/pdf"})
        params = {"version": "completed"}

        response = requests.get(full_url, params=params, headers=headers)
        data = b64encode(response.content)

        regex = "filename=(.[^;]+)"
        cd = response.headers.get("Content-Disposition")
        names = re.findall(regex, cd)
        filename = names[0]

        # Si la requête de signature n'a qu'un seul PDF, renvoi un pdf
        # Autrement renvoi un .zip
        # Dans tous les cas, un seul fichier/archive est récupéré
        attach = self.env["ir.attachment"].create(
            {
                "name": filename,
                "res_id": self.res_id,
                "res_model": self.model,
                "datas": data,
                "name": filename,
            }
        )
        self.write(
            {
                "signed_attachment_id": attach,
                "state": "archived",
            }
        )

        return False
