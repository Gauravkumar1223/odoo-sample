//** @odoo-module **/
import { Component, onMounted, useState } from '@odoo/owl';
import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';
import { standardFieldProps } from '@web/views/fields/standard_field_props';
import { _t } from 'web.core';

export class VoiceRecorder extends Component {
    constructor() {
        super(...arguments);
        this._resetState();
    }

    setup() {
        this.rpc = useService('rpc');
        this.notification = useService('notification');

        this.transcribeFieldName = this.props.transcription;
        this.modelName = this.props.record.resModel || 'wrrrit.ai.voice_record';

        onMounted(() => {
            this.loadRecording();
        });
    }

    _resetState() {
        this.state = useState({
            recording: false,
            audioURL: null,
            hasRecording: false,
            audioPlaying: false,
            playBlinking: false,
            transcribed: this.props.record.data[this.transcribeFieldName]
        });
    }

    async update(nextProps) {
        await super.update(nextProps);

        if (this.props.record.data.id !== nextProps.record.data.id) {
            this._resetState();
            this.loadRecording();
        } else if (this.props.record.data[this.props.name] !== nextProps.record.data[this.props.name]) {
            this.loadRecording();
        }
    }

    async loadRecording() {
        if (!this.props.record || !this.props.record.data || !this.props.record.data.id) {
            this.notification.add(_t('Record does not exist or is not saved yet.'), { type: 'warning' });
            return;
        }

        const modelName = this.modelName;
        const fieldName = this.props.name;

        try {
            const voiceRecord = await this.rpc('/web/dataset/call_kw', {
                model: modelName,
                method: 'read',
                args: [this.props.record.data.id, [fieldName]],
                kwargs: {},
            });

            if (voiceRecord && Array.isArray(voiceRecord) && voiceRecord.length > 0 && typeof voiceRecord[0][fieldName] === 'string') {
                const audioBlob = this.base64ToBlob(voiceRecord[0][fieldName]);
                if (audioBlob instanceof Blob) {
                    this.state.audioURL = URL.createObjectURL(audioBlob);
                    this.state.hasRecording = true;
                }
            } else {
                this.state.hasRecording = false;
            }
        } catch (error) {
            this.notification.add(_t('Error loading recording: ') + error.message, { type: 'danger' });
            throw error;
        }
    }

    padBase64(base64String) {
        while (base64String.length % 4 !== 0) {
            base64String += '=';
        }
        // console.log('Padded base64 string:', base64String);
        return base64String;
    }

    base64ToBlob(base64) {
        if (!base64) return null;
        let data = atob(this.padBase64(base64));
        let bytes = new Uint8Array(data.length);
        for (let i = 0; i < data.length; i++) {
            bytes[i] = data.charCodeAt(i);
        }
        // console.log('Converted base64 to Uint8Array:', bytes);
        return new Blob([bytes], { type: 'audio/mp3' }); // changed MIME type here
    }

    async saveRecording(blob) {
        if (!this.props.record || !this.props.record.data || !this.props.record.data.id) {
            this.notification.add(_t('Record does not exist or is not saved yet.'), { type: 'warning' });
            return;
        }
        const fieldName = this.props.name;
        const modelName = this.modelName;
        const reader = new FileReader();
        return new Promise((resolve, reject) => {
            reader.onloadend = async () => {
                let base64data = reader.result;
                base64data = base64data.split(',')[1];
                // console.log('Saving recording. Converted Blob to base64:', base64data);
                try {
                    const result = await this.rpc('/web/dataset/call_kw', {
                        model: modelName,
                        method: 'write',
                        args: [[this.props.record.data.id], { [fieldName]: base64data }],
                        kwargs: {},
                    });
                    this.notification.add(_t("Recording saved successfully."), { type: 'success' });
                    return result;
                } catch (error) {
                    this.notification.add(_t("Error saving recording: ") + error.message, { type: 'danger' });
                    throw error;
                }
                // console.log('saveRecording RPC response:', result);
                resolve(result);
            };
            reader.onerror = reject;
            reader.readAsDataURL(blob);
        });
    }

    async recordVoice() {
        console.log('recordVoice called. Current protocol:', location.protocol);

        if (this.state.recording) {
            console.log('Stopping the recording.');
            this.recorder.stop();
            this.gumStream.getAudioTracks()[0].stop();
            this.state.recording = false;
        } else {
            console.log('Starting a new recording.');
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.gumStream = stream;

            if (!this.recorder || this.recorder.state === 'inactive') {
                this.chunks = [];  // Reset chunks if the recorder is inactive or undefined
                this.recorder = new MediaRecorder(stream);
            }

            this.recorder.ondataavailable = (event) => {
                this.chunks.push(event.data);
            };

            this.recorder.onstop = async () => {
                const blob = new Blob(this.chunks, { type: 'audio/mp3' }); // Changed MIME type here
                this.state.audioURL = URL.createObjectURL(blob);
                console.log('Recording stopped. Saving the recording.');
                await this.saveRecording(blob);
            };

            this.recorder.start();
            this.state.recording = true;
        }
    }

    playRecording() {
        if (!this.audio) {
            this.audio = new Audio(this.state.audioURL);
            this.audio.onended = () => {
                this.audio = null;
                this.state.audioPlaying = false;
            };
            this.audio.play();
            this.state.audioPlaying = true;
        } else {
            this.stopAudio();
        }
    }
    stopAudio() {
        if (this.audio) {
            this.audio.pause();
            this.audio.currentTime = 0; // Reset audio to the beginning
            this.audio = null;
            this.state.audioPlaying = false;
        }
    }


    async startRecording() {
        console.log('Starting Recording');
        if (this.recorder && this.recorder.state === 'paused') {
            this.recorder.resume();
        } else if (!this.recorder || this.recorder.state === 'inactive') {
            await this.recordVoice();
        }
    }

    pauseRecording() {
        console.log('Pausing Recording');
        if (this.recorder && this.recorder.state === 'recording') {
            this.recorder.pause();
        }
    }

    playAudio() {
        console.log('Playing Audio');
        if (!this.audio) {
            this.audio = new Audio(this.state.audioURL);
            this.audio.onended = () => {
                this.audio = null;
            };
        }
        if (this.audio.paused) {
            this.audio.play();
        }
    }

    pauseAudio() {
        console.log('Pausing Audio');
        if (this.audio && !this.audio.paused) {
            this.audio.pause();
        }
    }

    restartAudio() {
        console.log('Restarting Audio');
        if (this.audio) {
            this.audio.currentTime = 0;
            this.audio.play();
        }
    }

    stopRecording() {

        if (this.recorder && this.recorder.state === 'recording') {
            console.log('Stopping Recording');
            this.recorder.stop();
            this.gumStream.getAudioTracks()[0].stop();
            this.state.recording = false;

        }
    }

    async deleteRecording() {
        if (!this.props.record || !this.props.record.data || !this.props.record.data.id) {
            this.notification.add(_t('Record does not exist or is not saved yet.'), { type: 'warning' });
            return;
        } const fieldName = this.props.name;
        const modelName = this.modelName;
        // console.log('deleteRecording called for record:', this.props.record);
        if (this.props.record && this.props.record.data) {
            const result = await this.rpc('/web/dataset/call_kw', {
                model: modelName,
                method: 'write',
                args: [[this.props.record.data.id], { [fieldName]: null }],
                kwargs: {},
            });
            // console.log('deleteRecording RPC response:', result);

            this.state.audioURL = null;
            this.state.audioPlaying = false;
            this.state.recording = false;




        }
    }

    mounted() {
        // console.log('Component mounted. Loading recording.');
        this.loadRecording();
    }






}

VoiceRecorder.template = 'wrrrit_ai.VoiceRecorder';
VoiceRecorder.props = {
    ...standardFieldProps,
    model: { type: String, optional: true },
    voice: { type: String, optional: true },
    transcription: { type: String, optional: true },
};
VoiceRecorder.extractProps = ({ attrs }) => {
    return {
        model: attrs.options.model,
        voice: attrs.options.voice,
        transcription: attrs.options.transcription
    };
};

VoiceRecorder.supportedTypes = ['binary'];
registry.category('fields').add('wrrrit_recorder', VoiceRecorder);
