/** @odoo-module **/

import { KeepLast } from "@web/core/utils/concurrency";

export class DmsModel {
    constructor(orm, resModel, fields, archInfo, domain) {
        this.orm = orm;
        this.resModel = resModel;
        const { limit } = archInfo;
        this.fields = fields;
        this.limit = limit;
        this.domain = domain;
        this.keepLast = new KeepLast();
        this.pager = { offset: 0, limit: limit };
        this.records = [];
    }

    async load() {
        const records = await
            this.orm.call('dms.directory','get_tree_data', [], {
                domain : this.domain,
                limit : this.pager.limit,
                offset: this.pager.offset,
            });
        this.records = records;
    }
}
