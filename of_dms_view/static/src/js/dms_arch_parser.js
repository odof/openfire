/** @odoo-module */

import { XMLParser } from "@web/core/utils/xml";

export class DmsArchParser extends XMLParser {
    parse(arch) {
        const xmlDoc = this.parseXML(arch);
        const limit = xmlDoc.getAttribute("limit") || 80;
        return {
            limit,
        };
    }
}
