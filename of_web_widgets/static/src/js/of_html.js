/** @odoo-module **/

import { registry } from "@web/core/registry";
import { HtmlField } from "@web/views/fields/html/html_field";

export class OFHtmlField extends HtmlField {}


registry.category("fields").add("of_html", OFHtmlField);
