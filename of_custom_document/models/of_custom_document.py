# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
import contextlib
import io
import mimetypes
import os
import tempfile

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.mimetypes import guess_mimetype

from odoo.addons.of_utils.models.image import _get_pdf_from_img

try:
    from pdfminer.pdfdocument import PDFDocument
    from pdfminer.pdfparser import PDFParser
    from pdfminer.pdftypes import resolve1
    from pdfminer.psparser import PSLiteral
    from pdfminer.utils import decode_text
except ImportError:
    PDFParser = PSLiteral = PDFDocument = resolve1 = decode_text = None
import pymupdf

try:
    import pypdftk
except ImportError:
    pypdftk = None


class OFCustomDocument(models.Model):
    """Printable PDF document templates"""

    _name = "of.custom.document"
    _inherit = "mail.render.mixin"
    _description = __doc__
    _order = "sequence"

    name = fields.Char(size=250, required=True)
    print_address = fields.Boolean(string="Print address", help="Print the address of the company")
    print_header = fields.Boolean(string="Print header", help="Print the header of the company")
    body_html = fields.Html(string="Body", render_engine="qweb", translate=True, prefetch=True, sanitize=False)
    file_name = fields.Char(string="Filename")
    file = fields.Binary()
    fillable = fields.Boolean(string="Keep fillable", help="The pdf document will be fillable")
    sequence = fields.Integer(default=10)
    model_id = fields.Many2one(comodel_name="ir.model", string="Applies to")
    model = fields.Char(
        string="Related Document Model", related="model_id.model", index=True, store=True, readonly=True
    )
    pdf_field_ids = fields.One2many(
        comodel_name="of.custom.document.field", inverse_name="document_id", string="PDF fields", copy=True
    )
    # contextual action
    ref_ir_act_report = fields.Many2one(
        comodel_name="ir.actions.report",
        string="Print action",
        readonly=True,
        copy=False,
        help="Sidebar action to make this template available on records of the related document model",
    )

    @api.depends("model_id")
    def _compute_render_model(self):
        for template in self:
            template.render_model = template.model_id.model

    def copy(self, default=None):
        default = dict(default or {})
        default["name"] = _("%s (copy)") % self.name
        return super().copy(default)

    def get_pdf_fields_values(self, record):
        self.ensure_one()
        return {
            pdf_field.name: pdf_field._render_field("value", record.ids)[record.id]
            for pdf_field in self.pdf_field_ids
            if pdf_field.to_export
        }

    def format_html(self, record):
        self.ensure_one()
        return self.with_context(render_model=record._name)._render_field("body_html", record.ids)[record.id]

    def render_file(self, res_ids):
        self.ensure_one()
        if not self.file:
            return False
        attachment_obj = self.env["ir.attachment"].sudo()
        attachment = attachment_obj.search(
            [("res_model", "=", self._name), ("res_field", "=", "file"), ("res_id", "=", self.id)], limit=1
        )

        if not attachment:
            raise UserError(_("No attachment found for custom document : %s"), self.name)

        if not res_ids or not self.pdf_field_ids:
            # Ensure the stream can be saved in Image.
            if attachment.mimetype.startswith("image"):
                result = _get_pdf_from_img(attachment)
            else:
                result = base64.b64decode(attachment.datas)
            return result, "pdf"

        temp_file_paths = []
        pdf_docs = []
        streams_to_merge = []
        try:
            for record in self.env[self.render_model].browse(res_ids):
                values = self.get_pdf_fields_values(record)
                # on utilise la norme adobe pour les noms de champs
                # si le nom du chamnp se termine par _af_image, on le traite comme une image
                values_text = {k: v for k, v in values.items() if not k.endswith("_af_image")}
                values_image = {k: v for k, v in values.items() if k.endswith("_af_image")}

                file_path = attachment_obj._full_path(attachment.store_fname)
                fd, generated_pdf = tempfile.mkstemp(prefix="doc_joint_", suffix=".pdf")
                pdf_docs.append(fd)

                temp_file_paths.append(generated_pdf)
                pypdftk.fill_form(file_path, values_text, out_file=generated_pdf, flatten=not self.fillable)

                self._insert_images(generated_pdf, self.pdf_field_ids, values_image)

                streams_to_merge.append(open(generated_pdf, "rb"))

            if len(streams_to_merge) == 1:
                pdf_content = streams_to_merge[0].read()
            else:
                with self.env["ir.actions.report"]._merge_pdfs(streams_to_merge) as pdf_merged_stream:
                    pdf_content = pdf_merged_stream.getvalue()
        finally:
            for stream in streams_to_merge:
                stream.close()
            for fd in pdf_docs:
                os.close(fd)
            for path in temp_file_paths:
                with contextlib.suppress(OSError, IOError):
                    os.remove(path)
        return pdf_content, "pdf"

    @api.onchange("file")
    def onchange_file(self):
        pdf_field_obj = self.env["of.custom.document.field"]
        pdf_fields = pdf_field_obj
        if self.file:
            if file_name := self.file_name:
                mimetype = mimetypes.guess_type(file_name)[0]
            else:
                mimetype = False
            if not mimetype:
                mimetype = guess_mimetype(base64.b64decode(self.file))

            if mimetype == "application/pdf":
                # Si le document est de type pdf, on cherche s'il contient des champs éditables
                pre_vals = {f.name: f.value for f in self.pdf_field_ids}
                pf = io.BytesIO(base64.b64decode(self.file))
                parser = PDFParser(pf)
                doc = PDFDocument(parser)

                pages = resolve1(doc.catalog.get("Pages"))
                field_numbers = resolve1(doc.catalog.get("AcroForm", {})).get("Fields", [])
                page_kids = [str(ref) for ref in pages.get("Kids")]

                # permet de récupérer la liste des fields par page
                # car dans certains cas les fields ne portent pas l'attribut P
                pk_annots = {}
                for str_ref, page in [(str(ref), resolve1(ref)) for ref in pages.get("Kids")]:
                    annots = page.get("Annots")
                    if isinstance(annots, list):
                        pk_annots[str_ref] = [str(a) for a in annots]
                    elif isinstance(resolve1(annots), list):
                        pk_annots[str_ref] = [str(a) for a in resolve1(annots)]

                for i in field_numbers:
                    doc_field = resolve1(i)

                    page_ref = doc_field.get("P")

                    page_number = None
                    if page_ref:
                        page_number = page_kids.index(str(page_ref))
                    if not page_number:
                        str_i = str(i)
                        for str_page_ref, page_annots in pk_annots.items():
                            if str_i in page_annots:
                                page_number = page_kids.index(str_page_ref)
                                break

                    rect = doc_field.get("Rect")
                    x0 = None
                    x1 = None
                    y0 = None
                    y1 = None

                    if not rect:
                        # Si pas de rect, on va rechercher un enfant
                        # Pas sur, sur de cette strat
                        kids = doc_field.get("Kids")
                        if kids:
                            kid = resolve1(kids[0])
                            rect = kid.get("Rect")

                    if rect:
                        x0 = rect[0]
                        y0 = rect[1]
                        x1 = rect[2]
                        y1 = rect[3]

                    name = doc_field.get("T").decode("unicode-escape", "ignore")
                    value = pre_vals.get(name)
                    if not value:
                        field_value = doc_field.get("V")
                        if field_value:
                            if isinstance(field_value, str):
                                value = decode_text(field_value)
                            elif isinstance(field_value, PSLiteral):
                                value = field_value.name
                            # decode des bytes comme une chaine de caractères
                            elif isinstance(field_value, bytes):
                                try:
                                    value = field_value.decode("utf-8")
                                except UnicodeDecodeError:
                                    value = None

                    pdf_fields += pdf_field_obj.new(
                        {
                            "name": name,
                            "value": value,
                            "to_export": True,
                            "page_number": page_number,
                            "x0": x0,
                            "x1": x1,
                            "y0": y0,
                            "y1": y1,
                        }
                    )
        self.pdf_field_ids = pdf_fields

    def update_action(self):
        for document in self:
            action = document.ref_ir_act_report
            if not action:
                continue
            vals = {}
            if action.name != document.name:
                vals |= {
                    "name": document.name,
                    "print_report_name": f'"{document.name}"',
                    "report_name": document.name,
                }
            if action.model != document.model_id.model:
                vals |= {
                    "model": document.model_id.model,
                    "binding_model_id": document.model_id.id,
                }
            if vals:
                action.write(vals)

    def unlink_action(self):
        for template in self:
            if template.ref_ir_act_report:
                template.ref_ir_act_report.unlink()
        return True

    def create_action(self):
        action_report_obj = self.env["ir.actions.report"]
        for document in self:
            action = action_report_obj.create(
                {
                    "name": document.name,
                    "report_type": "qweb-pdf",
                    "model": document.model_id.model,
                    "print_report_name": f'"{document.name}"',
                    "report_name": f"of_custom_document.{document.id}",
                    "binding_model_id": document.model_id.id,
                    "binding_type": "report",
                }
            )
            document.write({"ref_ir_act_report": action.id})

        return True

    def write(self, vals):
        res = super().write(vals)
        if any(field in vals for field in ("name", "model_id")):
            self.update_action()
        return res

    def unlink(self):
        self.unlink_action()
        return super().unlink()

    @api.model
    def _insert_images(self, pdf_path, pdf_field_ids, values):
        image_data = {pdf_field: values.get(pdf_field.name, None) for pdf_field in pdf_field_ids}

        doc = pymupdf.open(pdf_path)

        for field, content in image_data.items():
            if content and (abs(field.x1 - field.x0) > 0) and (abs(field.y1 - field.y0) > 0):
                # on récupère toutes les infos du cadre et de l'image pour faire nos calculs
                start_x = field.x0
                end_x = field.x1
                start_y = field.y0
                end_y = field.y1
                width = abs(field.x1 - field.x0)
                height = abs(field.y1 - field.y0)
                # Content a été évalué précédemment, c'est un bytes contenu dans un string
                # exemple du format: "b'caractères en base 64'".
                # On va donc juste récupérer le contenu base64
                content = content[2:-1]

                img = base64.b64decode(content)
                pix = pymupdf.Pixmap(img)

                # si les valeurs du cadre sont supérieures ou égales a celles de l'images, pas de resize à faire
                ratio_w = width / pix.width
                ratio_h = height / pix.height
                h_to_move = 0.0
                w_to_move = 0.0
                # un resize du cadre est a faire car au moins une des deux valeurs de l'image est plus grande que
                # celle du cadre. On utilise que le ratio le plus petit car le insertImage rempli totalement le cadre
                if ratio_w < 1 or ratio_h < 1:
                    if ratio_w < ratio_h:
                        h_to_move = (height - ratio_w * pix.height) / 2
                    else:
                        w_to_move = (width - ratio_h * pix.width) / 2
                else:
                    h_to_move = (height - pix.height) / 2
                    w_to_move = (width - pix.width) / 2
                # on bouge les points du cadre ce qui a pour effet de changer la taille de l'image
                end_y -= h_to_move
                start_y += h_to_move
                end_x -= w_to_move
                start_x += w_to_move
                page = doc[field.page_number]
                page_height = page.rect[3]
                # on créer le cadre et on insère l'image
                rect = pymupdf.Rect(start_x, page_height - end_y, end_x, page_height - start_y)
                page.insert_image(rect, pixmap=pix)

        doc.saveIncr()
        doc.close()
