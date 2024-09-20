/** @odoo-module **/

import { session } from "@web/session";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

// Needed so that this is run after adding the menu entries
import {user_menu_items} from "@web/webclient/user_menu/user_menu_items";


function documentationItemOF(env) {
    const url = session.of_documentation_url;
    return {
        type: "item",
        id: "documentation",
        description: env._t("Documentation"),
        href: url,
        callback: () => {
            browser.open(url, "_blank");
        },
        sequence: 10,
    };
}

function supportItemOF(env) {
    const url = session.of_support_url;
    return {
        type: "item",
        id: "support",
        description: env._t("Support"),
        href: url,
        callback: () => {
            browser.open(url, "_blank");
        },
        sequence: 20,
    };
}

registry.category("user_menuitems").remove("documentation");
registry.category("user_menuitems").remove("support");
registry.category("user_menuitems").remove("odoo_account");
registry.category("user_menuitems").add("documentation", documentationItemOF);
registry.category("user_menuitems").add("support", supportItemOF);
