/** @odoo-module **/

import {registry} from '@web/core/registry';
import {useService} from "@web/core/utils/hooks";
import {standardFieldProps} from "@web/views/fields/standard_field_props";

const {Component, useState, onWillStart, onMounted} = owl;

export class MediaRecorderList extends Component {
    setup() {
        this.state = useState({
            record: {name: "", duration: 0, type: "audio", file: null, user_id: null},
            recordList: [],
            isEdit: false,
            activeId: false,
            users: [],
            selectedRecordId: null,
        });
        this.orm = useService("orm");
        this.model = "media.recorder";

        onWillStart(async () => {
            try {
                await this.getAllRecords();
                await this.loadUsers();

            } catch (error) {
                console.error("Error during onWillStart:", error);
            }
        });

        onMounted(() => {
            const WaveSurfer = window.WaveSurfer || WaveSurfer; // depending on how the library exposes itself
            console.log("Player.js :WaveSurfer:", WaveSurfer);
            this.wavesurfer = WaveSurfer.create({
                container: '#waveform-2',
                waveColor: 'violet',
                progressColor: 'purple'
            });
        });
    }


    editRecord(record) {
        this.state.editRecord = {...record};
        this.state.selectedRecordId = record.id;
    }

    async updateRecord() {
        if (this.state.editRecord && this.state.selectedRecordId !== null) {
            try {
                await this.orm.write(this.model, [this.state.selectedRecordId], this.state.editRecord);
                await this.getAllRecords();
                this.state.selectedRecordId = null; // Close the details view
                this.state.editRecord = null; // Reset editRecord state
            } catch (error) {
                console.error("Error updating the record:", error);
            }
        } else {
            console.error("No record is currently being edited.");
        }
    }


    async getAllRecords() {
        try {
            this.state.recordList = await this.orm.searchRead(this.model, [], ["name", "recording_date", "duration", "type", "user_id"]);
        } catch (error) {
            console.error("Error fetching all records:", error);
        }
    }

    async loadUsers() {
        try {
            this.state.users = await this.orm.searchRead('res.users', [], ['id', 'name']);
        } catch (error) {
            console.error("Error loading users:", error);
        }
    }

    async searchRecords(event) {
        try {
            const text = this.refs.searchInput.value;
            this.state.recordList = await this.orm.searchRead(this.model, [['name', 'ilike', text]], ["name", "duration", "type", "user_id"]);
        } catch (error) {
            console.error("Error searching records:", error);
        }
    }

    selectRow(event, recordId) {
        if (event && event.target && ["BUTTON", "A", "INPUT"].includes(event.target.nodeName.toUpperCase())) {
            event.stopPropagation();
            return;
        }
        this.state.selectedRecordId = this.state.selectedRecordId === recordId ? null : recordId;
    }

    resetForm() {
        this.state.record = {name: "", duration: 0, type: "audio", file: null, user_id: null};
    }

    addRecord() {
        this.resetForm();
        this.state.activeId = false;
        this.state.isEdit = false;
    }


    async saveRecord() {
        try {
            let recordData = {...this.state.record};
            recordData.recording_date = this.formatDateTimeForOdoo(recordData.recording_date);

            if (!this.state.isEdit) {
                await this.orm.create(this.model, [recordData]);
                this.resetForm();
            } else {
                await this.orm.write(this.model, [this.state.activeId], recordData);
            }
            await this.getAllRecords();
        } catch (error) {
            console.error("Error saving record:", error);
        }
    }

    async deleteRecord(record) {
        try {
            await this.orm.unlink(this.model, [record.id]);
            await this.getAllRecords();
        } catch (error) {
            console.error("Error deleting record:", error);
        }
    }

    cancelEdit() {
        this.state.selectedRecordId = null;
    }

    formatDateTimeForInput(dateTime) {
        return dateTime ? dateTime.replace(' ', 'T') : '';
    }

    formatDateTimeForOdoo(dateTime) {
        return dateTime ? dateTime.replace('T', ' ') : false;
    }

    handleInputChange(field, event) {
        // If record is not in the edit state, initialize it
        if (!this.state.editRecord) {
            this.state.editRecord = {...this.state.recordList.find(r => r.id === this.state.selectedRecordId)};
        }
        // Update the field on the edit record
        this.state.editRecord[field] = event.target.value;
    }


}

MediaRecorderList.template = 'media.RecorderList';
MediaRecorderList.props = {...standardFieldProps};
registry.category('actions').add('media.action_recorder_list_js', MediaRecorderList);