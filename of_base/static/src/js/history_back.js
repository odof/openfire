/** @odoo-module **/

import { registry } from "@web/core/registry";


export function doHistoryBackClientAction(env, action) {
    window.history.back();
}

registry.category("actions").add("history_back", doHistoryBackClientAction);