/** @odoo-module **/
const { Component, useState } = owl;
import { TreeRecord } from "./tree_record";

export class PopupoverInfo extends Component {
   static template = "of_sale_layout_category.popupover_info";
}

export class PopupoverDelete extends Component {
    static template = "of_sale_layout_category.popupover_delete";

   setup(){
      this.sections = [];
      // on va chercher les enfants de la section en cours pour ne pas déplacer la section en cours dedans
      this.treeRecord = new TreeRecord(this.props.options.line.props.list);
      let recordNode = this.treeRecord.find(this.props.options.record.id);
      let childrenNodes = this.treeRecord.allChildren(recordNode);
      let childIds = [];
      for (let [key,value] of Object.entries(childrenNodes)) {
         childIds.push(key);
      }
      this.props.options.line.props.list.records.filter((record) => record.data.display_type == 'line_section' && !childIds.includes(record.id)).map((record) => {
         this.sections.push({
            id : record.data.of_node_id,
            name : `${record.data.of_section_name} - ${record.data.name}`,
         });
      })

      this.state = useState({
         'section': "all",
         'sectionSelected': false,
      });
   }

   cancel(evt){
      this.props.close();
   }

   async delete(evt){
      if (this.state.section == 'all'){
         // on supprime la section et tout ce qui est en dessous
         await this.props.options.line.delete(evt);
      } else {
         // on déplace d'abord les sous-sections
         let children = this.props.options.line.props.list.records.filter((record) => record.data.of_parent_node_id == this.props.options.line.props.record.data.of_node_id);
         await Promise.all(children.map(async (child) => {
            // on modifie juste le of_parent_node_id avec l'id de la section sélectionnée
            await child.update({
               'of_parent_node_id': this.state.sectionSelected
            })
         }));
         // puis on supprime la section en question
         await this.props.options.line.delete(evt);
      }

      this.props.close();
   }
}
