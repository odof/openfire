/** @odoo-module **/

import { RelationalModel } from "@web/views/relational_model";

export class MapModel extends RelationalModel {
    setup(params, { action, dialog, notification, rpc, user, view, company }) {
        this.rootType = "map";
        super.setup(...arguments);
    }
}
