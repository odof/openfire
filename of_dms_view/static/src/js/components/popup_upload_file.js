/** @odoo-module **/

import { Component, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";


export class PopupUploadFile extends Component {
    static template = "of_dms_view.PopupUploadFile";

    setup(){
        this.inputRef = useRef('input_file');
        this.orm = useService("orm");
    }

    click_close(){
        this.props.close();
    }

    click_upload(){
        var self = this;
        let file = this.inputRef.el.files;
        if (file.length>0){
            var reader = new FileReader();
            reader.readAsDataURL(file[0]);

            reader.onload = async function (e) {
                let data = {
                    'name': file[0].name,
                    'datas': reader.result.split(',')[1],
                    'res_model': 'res.partner',
                    'res_id': self.props.record.model_id
                }

                let res = await self.orm.create('ir.attachment',[data]);
                await self.props.options.bus.trigger("refresh_directories_files", {});
                self.props.close();
            };
        }
    }
}
