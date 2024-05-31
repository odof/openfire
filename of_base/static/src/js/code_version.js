/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onMounted } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";

class DisplayCodeVersion extends Component {
    static components = {
        ...Component.components,
        Dropdown,
        DropdownItem,
    };
    setup() {
        this.rpc = useService("rpc");
        this.state = useState({
            code_version: "",
        });
        onMounted(this.fetchVersion.bind(this));
    }

    async fetchVersion() {
        const version_data = await this.rpc("/openfire/version", {} );
        this.state.code_version = version_data.version;
    }
}
DisplayCodeVersion.template = "of_base.DisplayCodeVersion";
DisplayCodeVersion.props = {};

export const systrayItem = {
    Component: DisplayCodeVersion,
    isDisplayed: (env) => env.services.user.isSystem,
};

registry.category("systray").add("DisplayCodeVersion", systrayItem, { sequence: 1 });
