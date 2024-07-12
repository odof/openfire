/** @odoo-module **/

import { Component, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";


export class PopupDeleteFile extends Component {
    static template = "of_dms_view.PopupDeleteFile";

    setup(){
        this.orm = useService("orm");
    }

    click_close(){
        this.props.close();
    }

    async click_delete(){
        await this.props.options.bus.trigger("hide_preview", {});
        await this.orm.unlink('ir.attachment',[this.props.currentFile.attachment_id]);
        await this.props.options.bus.trigger("refresh_directories_files", {});
        this.props.close();
    }
}
