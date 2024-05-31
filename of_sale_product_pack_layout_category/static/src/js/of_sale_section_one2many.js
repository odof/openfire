/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { OFSaleSectionLine, OFSaleSectionListRenderer } from "@of_sale_layout_category/js/of_sale_section_one2many";

import { TreeRecord } from "@of_sale_layout_category/js/tree_record";

patch(OFSaleSectionLine.prototype,"OFSaleSectionLine", {
    async duplicate(evt) {
        // Ici, il faut faire attention, un kit peut avoir des composants, on ne doit dupliquer que les lignes de kits.
        // Le principe c'est de générer le treeRecord, pour récupérer la liste des enfants de la section à dupliquer et
        // de faire un simple add sur chacun des enfants
        let children = this.props.list.records.filter((record) => record.data.of_parent_node_id == this.props.record.data.of_node_id);

        // D'abord, on duplique le node en cours, c'est un add avec des différences
        let recordValue = this.props.record.data;
        recordValue['of_node_id'] = this.props.list.records.length + 1;
        recordValue['of_parent_node_id'] = this.props.record.data.of_parent_node_id;
        if (!recordValue['pack_parent_line_id']){
            let newRecord = await this.add(recordValue);


            if (children.length > 0) {
                await this.duplicateRecursive(newRecord, children);
            }

            // A la fin on lance un resequence pour calculer la séquence et le nom des sections
            await this.resequence();
        }
    },

    async duplicateRecursive(parentRecord, children) {
        await Promise.all(children.map(async (child) => {
            // On va chercher les enfants (même of_node_parent_id dans les records)
            let childs = this.props.list.records.filter((record) => record.data.of_parent_node_id == child.data.of_node_id);
            // On duplique le child
            let recordValue = child.data;
            recordValue['of_node_id'] = this.props.list.records.length + 1;
            recordValue['of_parent_node_id'] = parentRecord.data.of_node_id;
            if (!recordValue['pack_parent_line_id']){
                let newRecord = await this.add(recordValue);
                // On les duplique récursivement s'il y en a
                if (childs.length > 0) {
                    await this.duplicateRecursive(newRecord, childs);
                }
            }
        }));
    },

    async delete(evt) {
        // Ici, on ne peut supprimer que les kits et non les composants.
        // Le principe c'est de générer le treeRecord, pour récupérer la liste des enfants de la section à supprimer
        // et de faire un simple remove sur chacun des enfants.
        let treeRecord = new TreeRecord(this.props.list);
        let node = treeRecord.find(this.props.record.id);
        for (let child of Object.entries(treeRecord.allChildren(node))) {
            if (child[0] != "Root") {
                let child_record = this.props.list.records.find((record) => record.id == child[0]);
                if (!child_record.data.pack_parent_line_id){
                    await this.remove(child[0]);
                }
            }
        }
        // On finit par supprimer le node restant
        await this.remove(this.props.record.id);

        // A la fin on lance un resequence pour calculer la sequence et le nom des sections
        await this.resequence();
    }

})

patch(OFSaleSectionListRenderer.prototype,"OFSaleSectionListRenderer", {
    async sortDrop(dataRowId, { element, previous }) {
        let record = this.props.list.records.find((record) => record.id == dataRowId);
        // Si on est sur une ligne de composant, on la remet là où elle était
        if (record.data.pack_parent_line_id){
            return;
        }

        if (this.props.list.editedRecord) {
            this.props.list.unselectRecord(true);
        }
        element.classList.remove("o_row_draggable");
        const refId = previous ? previous.dataset.id : null;
        try {
            this.resequencePromise = this.props.list.resequence(dataRowId, refId, {
                handleField: this.props.archInfo.handleField,
            });
            await this.resequencePromise;
        } finally {
            element.classList.add("o_row_draggable");
        }


        // On doit vérifier deux cas, soit l'élément déplacé est une section, soit c'est un article/note.
        // Si c'est une section, on modifie la `of_position_node` et une resequence pour la placer au bon endroit
        // sinon, on modifie le of_parent_node_id de l'élément pour lui donner celui de son prédécesseur
        if (record.data.display_type == 'line_section') {
            // on récupère l'ordre des enfants
            let brothers = this.props.list.records.filter((r) => r.data.of_parent_node_id == record.data.of_parent_node_id);
            await Promise.all(brothers.map(async (r, index) => {
                await r.update({ 'of_position_node': index });
            }));
            await this.resequence();
        } else {

            let indexRecord = this.props.list.records.indexOf(record);
            if (indexRecord == 0) {
                await record.update({
                    'of_parent_node_id': 0, // le parent est forcément la racine
                    'of_position_node': this.props.list.records.length
                })

            } else {
                // Il faut prendre le record d'avant qui est une section
                let previousSectionRecords = this.props.list.records.filter((record) => record.data.display_type == 'line_section');
                let previousSectionRecord = false;
                previousSectionRecords.map((r) => {
                    if (r.data.sequence < record.data.sequence) {
                        previousSectionRecord = r;
                    }
                })
                let index = 0;
                let of_node_id = 0;
                if (previousSectionRecord) {
                    of_node_id = previousSectionRecord.data.of_node_id
                }

                let children = this.props.list.records.filter((record) => record.data.of_parent_node_id == of_node_id);
                if (children) {
                    index = children.length;
                }
                await record.update({
                    'of_parent_node_id': of_node_id,
                    'of_position_node': index,
                })


            }
            await this.move_composants(record);

        }
    },
    async move_composants(record){
        // On va chercher les composants du kit à déplacer s'il y en a, pour leur donner le même parent du coup
        let composant_records = this.props.list.records.filter((r) => r.data.pack_parent_line_id && r.data.pack_parent_line_id[0] == record.data.id);
        let {sequence} = record.data;
        for (const r of composant_records){
            sequence += 1;
            await r.update({
                'of_parent_node_id': record.data.of_parent_node_id,
                'of_position_node': record.data.of_position_node,
                'sequence': sequence,
            })
            r.model.notify();
        }
        this.resequence();
    }

});
