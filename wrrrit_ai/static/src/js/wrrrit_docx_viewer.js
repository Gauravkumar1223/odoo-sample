/** @odoo-module **/

// Import necessary dependencies from Odoo's web module
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component } from "@odoo/owl";
owl.Component.mode = "prod";
// Define the DocxViewer component
export class DocxViewer extends Component {

    // setup method is called when the component is being created
    setup() {
        this.recordId = this.props.record.data.id;  // Store the record ID from the props
        this.baseUrl = `${window.location.protocol}//${window.location.host}/`;  // Get the base URL of the current Odoo instance

    }

    // Getter method for constructing the iframe source URL
   get iframeSrc() {
    // Construct the document URL on the Odoo server
    const docUrl = `${window.location.hostname}/wrrrit_get_docx/${this.recordId}`;


    // Encode the document URL for use in the Office Online Viewer URL
    const encodedUrl = docUrl;


    // Construct and return the Office Online Viewer URL
    const viewerUrl = `https://view.officeapps.live.com/op/view.aspx?src=${encodedUrl}`;

    return viewerUrl;
}

    // ... rest of your code ...
}

// Set the QWeb template for the component
DocxViewer.template = "wrrrit_ai.DocxViewer";

// Define the props expected by the component
DocxViewer.props = {
    ...standardFieldProps,
    record: {
        type: Object,
    },
};

// Define a method for extracting props from template attributes
DocxViewer.extractProps = ({attrs}) => {
    let options = attrs.options || {};  // Ensure that options are available even if undefined
    return {
        record: options.record || {},
    };
};

// Register the DocxViewer component with Odoo's field registry
registry.category("fields").add("docx_viewer", DocxViewer);
