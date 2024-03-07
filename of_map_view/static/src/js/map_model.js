/** @odoo-module */

import {Model} from "@web/views/model";

export class MapModel extends Model {
    setup(params, {}) {
        this.data = {
            count: 0,
            records: [],
            recordIds: [],
            records: [],
        };
        this.metaData = {
            ...params,
        };
    }

    /**
     *
     * @param { Object } params
     */
    async load(params) {
        const metaData = {
            ...this.metaData,
            ...params,
        };
        this.data.records = await this._fetchData(metaData);
        this.data.recordIds = [];
        this.data.records.records.map((record) => {
            this.data.recordIds.push(record.id);
        });

        this.notify();
    }

    /**
     *
     * @param { Object } metaData
     * @returns
     */
    async _fetchData(metaData) {
        var decorationFields = metaData.decorationFields;
        decorationFields.push(
            metaData.latitudeField,
            metaData.longitudeField,
            'id',
        );
        return this.orm.webSearchRead(
            metaData.resModel,
            metaData.domain,
            decorationFields,
            {
                order: metaData.orderBy.join(" "),
                context: metaData.context,
            }
        );
    }
}
