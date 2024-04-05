/** @odoo-module **/


export class TreeRecord {

    // Un treeRecord est constitué d'une racine (this.root), dont la 'key' est Root
    // et des enfants (children), qui sont des nodes, dont les 'key' sont les
    // dataPointId des records d'odoo

    constructor(value) {
        this.value = value;
        this.root = new TreeNode('Root');
        this.loadTree();
    }

    *preOrderTraversal(node = this.root) {
        yield node;
        if (node.hasChildren) {
          for (let child of node.children) {
            yield* this.preOrderTraversal(child);
          }
        }
      }

     find(key) {
      for (let node of this.preOrderTraversal()) {
        if (node.key === key) return node;
      }
      return undefined;
    }

    loadTree(){
        // on trie les records par ordre de sequence et de of_position_node
        // cela va permettre de créer l'arbre en étant sûr que le noeud parent existe
        var records = this.value.records.toSorted(
            (r1,r2) =>
                r1.data.sequence - r2.data.sequence ||
                r1.data.of_position_node - r2.data.of_position_node
            );

        // construction du treerecord
        records.map((record) => {
            let parentNodeId = record.data.of_parent_node_id;
            if (parentNodeId == 0){
                this.insertLast("Root",record.id);
            } else {
                let parentRecord = records.find((record) => record.data.of_node_id == parentNodeId);
                if (parentRecord){
                    this.insertLast(parentRecord.id,record.id);
                } else {
                    console.log("Hmm something went wrong on loadTree : ",record);
                }
            }
        });
    }

    insertLast(parentNodeKey,key){
        for (let node of this.preOrderTraversal()) {
          if (node.key === parentNodeKey) {
            node.children.push(new TreeNode(key, node));
            return true;
          }
        }
        return false;
    }

    insertFirst(parentNodeKey,key){
        for (let node of this.preOrderTraversal()) {
          if (node.key === parentNodeKey) {
            node.children.unshift(new TreeNode(key, node));
            return true;
          }
        }
        return false;
    }

    insertAfter(parentNodeKey,previousNodeKey,key){
        for (let node of this.preOrderTraversal()) {
            if (node.key === parentNodeKey){
                let previousNode = this.find(previousNodeKey);
                let index = node.children.indexOf(previousNode);
                node.children.splice(index,0,new TreeNode(key,node));
                return true
            }
        }
        return false;
    }

    remove(key){
        for (let node of this.preOrderTraversal()) {
          const filtered = node.children.filter(c => c.key !== key);
          if (filtered.length !== node.children.length) {
            node.children = filtered;
            return true;
          }
        }
        return false;
    }

    setSequence(node=this.root,index=0){
        if (node.key != "Root"){
            node.sequence = index;
        }
        var nextIndex = index+1;
        if (node.hasChildren){
            node.children.map((child) => {
                nextIndex = this.setSequence(child,nextIndex);
            });
        }
        return nextIndex;
    }

    // on crée les noms des records, basée sur la relation parent/enfants
    // on vérifie que nous ne sommes que sur des sections
    setName(node=this.root,parentName="Root"){
        let index = 0;
        node.children.map((child) => {
            let record = (this.value.records.find((record) => record.id == child.key));
            if (record.data.display_type == 'line_section'){
                if (parentName != "Root"){
                    child.name = `${parentName}.${index + 1}`;
                } else {
                    child.name = `${index + 1}`;
                }
                this.setName(child,child.name);
                index += 1;
            }
        });
    }

    // on calcule la profondeur des sections, utilisée pour choisir la couleur de fond de la section
    setLevel(node=this.root,level=0){
        if (node.key != "Root"){
            node.level = level;
        }
        var nextLevel = level+1;
        if (node.hasChildren){
            node.children.map((child) => {
                this.setLevel(child,nextLevel);
            });
        }
    }

    get data(){
        // cette fonction permet d'exporter les données du tree sous forme de liste
        // L'idée c'est d'utiliser ces données pour mettre à jour les records odoo
        let records = {};
        this.setSequence();
        this.setName();
        this.setLevel();

        for (let node of this.preOrderTraversal()) {
            records[node.key] = {
                'of_section_name': node.name,
                'sequence': node.sequence,
                'of_level': node.level,
            }
        }
        return records;
    }

    allChildren(node){
        let children = {};
        for (let n of this.preOrderTraversal(node)){
            children[n.key] = {
                'of_section_name': n.name,
                'sequence': n.sequence,
            }
        }
        return children;
    }

    info(dataPointId){
        let record = this.value.records.find((record) => record.id == dataPointId);
        if (record){
            return record.data;
        }
    }

    html(node=this.root){
        var code = "<ul class='tree'>";
        if (node.hasChildren){
            for(let c of node.children){
                let data = this.info(c.key);
                code += "<li>" + c.name + " (" + c.sequence + ")(" + data.of_position_node + ")(" + c.level + ") - " + data.name + this.html(c) + "</li>";
            }
            code += "</ul>";
        } else {
            code = ""
        }
        return code;
    }

}


class TreeNode {
    constructor(key,parentNode){
        this.key = key;
        this.parent = parentNode;
        this.children = [];
        this.sequence = 0;
        this.name = "";
        this.level = 0;
    }

    get isLeaf(){
        return this.children.length === 0;
    }

    get hasChildren(){
        return !this.isLeaf;
    }
}
