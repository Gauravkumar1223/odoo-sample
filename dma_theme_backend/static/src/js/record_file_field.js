/** @odoo-module **/

import { _lt, _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { isBinarySize, toBase64Length } from "@web/core/utils/binary";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { Component } from "@odoo/owl";

export const MAX_FILENAME_SIZE_BYTES = 0xFF;  // filenames do not exceed 255 bytes on Linux/Windows/MacOS

export class RecordFileField extends Component {
    get hasFile() {
        return this.props.type === "binary";
    }

    get title() {
        return this.props.record.data.name;
    }

    get fileSize() {
        const encoded = this.props.value;
        // Decode the base64 string to get the size in bytes
        const decoded = atob(encoded);
        // Return the size in bytes, kilobytes, megabytes with the unit
        const size = decoded.length;
        if (size < 1024) {
            return _t("%s B").replace("%s", size);
        } else if (size < 1024 * 1024) {
            return _t("%s KB").replace("%s", (size / 1024).toFixed(2));
        } else {
            return _t("%s MB").replace("%s", (size / 1024 / 1024).toFixed(2));
        }
    }
}

RecordFileField.template = "web.RecordFileField";
RecordFileField.props = {
    ...standardFieldProps
};

RecordFileField.displayName = _lt("File Size");
RecordFileField.supportedTypes = ["binary"];

registry.category("fields").add("record_file", RecordFileField);
