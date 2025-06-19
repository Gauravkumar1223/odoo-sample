//** @odoo-module **/

import {registry} from '@web/core/registry';
import {useService} from '@web/core/utils/hooks';
import {standardFieldProps} from '@web/views/fields/standard_field_props';
import {loadJS} from "@web/core/assets";
import Dialog from 'web.Dialog';
import {_lt} from "@web/core/l10n/translation";

import {
    Component,
    onMounted,
    onWillStart,
    onWillUnmount,
    onWillUpdateProps,
    useEffect,
    useRef,
    useState
} from '@odoo/owl';

export class VoiceRecorder extends Component {
    setup() {

        this.state = useState({
            recording: false,
            isRecording: false,
            audioURL: null,
            pauseAudio: false,
            transcribing: false,
            transcription: '',
            transcript: '',
            correct_transcript: '',
            hasRecording: false,
            audioPlaying: false,
            playBlinking: false,
            transcribed: this.props.record.data[this.transcribeFieldName],
            currentTimeMinutes: "00",
            currentTimeSeconds: "00",
            currentTimeMilliseconds: "000",
            recordingStatus: 'inactive',
            totalDuration: 0,
            rt_transcription: "",
            startTime: 0,// Start time of the recording
            currentTime: 0, // Current time of the recording
            intervalId: null, // ID of the interval timer
            pausetime: 0,
            totalPausedTime: 0,
            lastPauseTimestamp: 0,
            selectedLanguage: 'de'


        });

        this.user = useService('user');

        this.transcriptions = {};
        this.action = useService("action")
        this.rpc = useService('rpc');
        this.notification = useService('notification');

        this.transcribeFieldName = this.props.transcription;
        this.modelName = this.props.record.resModel || 'wrrrit.ai.voice_record';
        this.audio = null;
        this.blobBytes = 0;

        this.audioContext = null;
        this.recorder = null;
        this.gumStream = null;
        this.socket = null;
        this.transcriptionsRef = useRef("textareaRef");

        this.waveformRef = null;
        this.containerRef = useRef("correct_transcript");
        this.wavesurfer = null;
        this.saveButton = document.querySelector('button.o_form_button_save');
        this.model = "deepgram"

        onWillStart(async () => {
            await loadJS(
                "https://unpkg.com/wavesurfer.js@7"
            );
            await loadJS(
                "https://unpkg.com/wavesurfer.js@7.7.1/dist/plugins/record.min.js"
            );
        });

        onWillUnmount(() => {
            this.resetState();
        });

        useEffect(() => {
            this.resetState();
            this.loadRecording().then(() => {
                this.state.transcript = this.props.record.data[this.transcribeFieldName] || '';
                const saveButton = document.querySelector('button.o_form_button_save');
                if (saveButton) {
                    saveButton.click();
                }
            });
        }, () => [this.props.record.data.id]);

        onMounted(async () => {
            this.resetState();
            await this.loadRecording();
            this.state.transcript = this.props.record.data[this.transcribeFieldName] || '';
            const saveButton = document.querySelector('button.o_form_button_save');
            if (saveButton) {
                saveButton.click();
            }
            this.waveformRef = document.getElementById('audio-visualizer');
            if (this.state.audioURL) {
                this.createPlayWaveSurfer();
            } else {
                this.initWaveSurfer();
                this.initMicSelect();
            }
        });

        onWillUpdateProps((nextProps) => {
            if (this.props.record.data.id !== nextProps.record.data.id) {
                this.resetState();

                this.loadRecording().then(() => {
                    this.state.transcript = nextProps.record.data[this.transcribeFieldName] || '';
                    this.saveButton = document.querySelector('button.o_form_button_save');
                    if (this.saveButton) {
                        this.saveButton.click();
                    }
                })
            }
        });
    }

    resetState() {
        if (this.audio) {
            //this.audio.stop();
             this.wavesurfer.stop();
            this.audio = null;
        }

        // Reset all relevant state properties to their initial values
        Object.assign(this.state,
            {
                recording: false,
                isRecording: false,
                audioURL: null,
                pauseAudio: false,
                transcribing: false,
                transcription: '',
                transcript: '',
                hasRecording: false,
                audioPlaying: false,
                playBlinking: false,
                transcribed: "",
                totalPausedTime: 0,
                lastPauseTimestamp: null,
                currentTimeMinutes: "00",
                currentTimeSeconds: "00",
                currentTimeMilliseconds: "000",
                recordingStatus: 'inactive',
                totalDuration: 0,
                rt_transcription: "",
                startTime: 0,// Start time of the recording
                currentTime: 0, // Current time of the recording
                intervalId: null, // ID of the interval timer
                pausetime: 0,
                selectedLanguage: 'de',
                correct_transcript: '',
            });

        // Add any other properties that need to be reset
        this.waveformRef = document.getElementById('audio-visualizer');
        if (this.state.audioURL) {
            this.createPlayWaveSurfer();
        } else {
            this.initWaveSurfer();
            this.initMicSelect();
        }
    }

    async update(nextProps) {

        super.update(nextProps);

        if (this.props.record.data.id !== nextProps.record.data.id) {
            this.resetState();
            await this.loadRecording();
        } else if (
            this.props.record.data[this.props.name] !==
            nextProps.record.data[this.props.name]
        ) {
            await this.loadRecording();
        }
    }

    async loadRecording() {
        if (
            !this.props.record ||
            !this.props.record.data ||
            !this.props.record.data.id
        ) {
            return;
        }

        const modelName = this.modelName;
        const fieldName = this.props.name;

        try {
            const voiceRecord = await this.rpc('/web/dataset/call_kw', {
                model: modelName,
                method: 'read',
                args: [this.props.record.data.id, [fieldName, 'corrected_transcription_data']],
                kwargs: {},
            });

            if (
                voiceRecord &&
                Array.isArray(voiceRecord) &&
                voiceRecord.length > 0 &&
                typeof voiceRecord[0][fieldName] === 'string'
            ) {
                const audioBlob = this.base64ToBlob(voiceRecord[0][fieldName]);
                if (audioBlob instanceof Blob) {
                    this.state.audioURL = URL.createObjectURL(audioBlob);
                    this.state.hasRecording = true;
                }
                if (voiceRecord[0]['corrected_transcription_data']) {
                    this.state.correct_transcript = voiceRecord[0]['corrected_transcription_data'] || '';
                }
            } else {
                this.state.hasRecording = false;
            }

        } catch (error) {
            this.notification.add(_lt('Error loading recording: ') + error.message, {
                type: 'danger',
            });
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
        return new Blob([bytes], {type: 'audio/mp3'}); // changed MIME type here
    }

    async saveRecording(blob) {
        if (
            !this.props.record ||
            !this.props.record.data ||
            !this.props.record.data.id
        ) {
            this.notification.add(_lt('Record does not exist or is not saved yet.'), {
                type: 'warning',
            });
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
                        args: [[this.props.record.data.id], {[fieldName]: base64data}],
                        kwargs: {},
                    });
                    this.notification.add(_lt('Recording saved successfully.'), {
                        type: 'success',
                    });
                    return result;
                } catch (error) {
                    this.notification.add(
                        _lt('Error saving recording: ') + error.message,
                        {type: 'danger'}
                    );
                    throw error;
                }


            };
            reader.onerror = reject;
            reader.readAsDataURL(blob);
        });
    }

    async recordVoice(state) {
        const saveButton = document.querySelector('button.o_form_button_save');
        // add a dialog to confirm if the user wants to save the record before recording

        const visualizerCanvas = document.getElementById('audio-visualizer'); // Get the existing canvas

        // Create an audio context and analyzer for visualizing the audio
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const analyzer = this.audioContext.createAnalyser();

        this.displayTimestamp();
        if (this.state.recording) {
            // console.log('Stopping the recording.');
            this.recorder.stop();
            this.gumStream.getAudioTracks()[0].stop();
            this.state.recording = false;
            this.state.isRecording = false;
            // Close the WebSocket connection when recording stops
            if (this.socket) {
                this.socket.close();
                this.socket = null;
            }
            // Stop the audio context to prevent feedback
            if (this.audioContext) {
                this.audioContext.close().catch((error) => {
                    // console.error('Error closing audio context:', error);
                });
            }
        } else {
            // console.log('Starting a new recording.');

            // Construct WebSocket URL
            let wsProtocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
            let wsPort =
                location.port && parseInt(location.port, 10)
                    ? parseInt(location.port, 10) + 1000
                    : location.protocol === 'wss:'
                        ? 443
                        : 80;
            let wsPath = 'realtime_transcribe';

            if (wsPort === 443) {
                // Prefix the path with 'custom_socket' if the port is 443
                wsPath = 'custom_socket/' + wsPath;
            }
            if (wsPort === 80) {
                wsPort = ""
                // Prefix the path with 'custom_socket' if the port is 443
                wsPath = 'custom_socket/' + wsPath;
            }
            const languageQueryParam = `language=${encodeURIComponent(this.state.selectedLanguage)}`; // Include the selected language as a query parameter

            // console.log('languageQueryParam :', languageQueryParam)
            let wsAddress = `${wsProtocol}//${location.hostname}:${wsPort}/${wsPath}?${languageQueryParam}`;
            // Open a new WebSocket connection when recording starts
            this.socket = new WebSocket(wsAddress);
            const constraints = {
                audio: {
                    sampleRate: 16000,
                    echoCancellation: true, // Enable echo cancellation
                    //output: false, // Prevent sound from being sent to the speakers
                },
            };

            try {
                const stream = await navigator.mediaDevices.getUserMedia(constraints);
                this.gumStream = stream;

                // Connect the media stream to the audio context and analyzer
                const source = this.audioContext.createMediaStreamSource(stream);
                source.connect(analyzer);

                // Set up the visualizer canvas
                const visualizerCanvasContext = visualizerCanvas.getContext('2d');
                visualizerCanvasContext.fillStyle = 'rgba(0, 0, 0, 0.5)';
                visualizerCanvasContext.strokeStyle = 'rgba(255, 255, 255, 0.7)';
                visualizerCanvasContext.lineWidth = 2;

                // Initialize the chunks array here
                this.chunks = [];

                // Function to draw the visualizer bars or waves
                const drawVisualizer = () => {
                    const dataArray = new Uint8Array(analyzer.frequencyBinCount);
                    analyzer.getByteFrequencyData(dataArray);

                    const canvasWidth = visualizerCanvas.width;
                    const canvasHeight = visualizerCanvas.height;
                    const barWidth = (canvasWidth / dataArray.length) * 2;
                    const numBars = dataArray.length;
                    const maxAmplitude = 255;

                    visualizerCanvasContext.clearRect(0, 0, canvasWidth, canvasHeight);

                    for (let i = 0; i < numBars; i++) {
                        const value = dataArray[i];
                        const barHeight = (value / maxAmplitude) * canvasHeight;

                        // Calculate the color based on a Gaussian-like distribution
                        const hue = (i / numBars) * 360; // Use hue to represent the color spectrum
                        const saturation = 100; // Full saturation
                        const lightness = 50 + (barHeight / canvasHeight) * 50; // Vary lightness with bar height

                        // Convert HSL color to RGB
                        visualizerCanvasContext.fillStyle = `hsl(${hue}, ${saturation}%, ${lightness}%)`;

                        // Create rectangles with varying heights
                        visualizerCanvasContext.fillRect(
                            i * barWidth,
                            canvasHeight - barHeight,
                            barWidth,
                            barHeight
                        );
                    }


                    requestAnimationFrame(drawVisualizer);


                };
                drawVisualizer();

                // Initialize the recorder here
                this.recorder = new MediaRecorder(stream);
                this.state.startTime = Date.now(); // Start time of the recording
                this.state.currentTime = 0; // Current time of the recording
                this.state.intervalId = null; // ID of the interval timer

                this.recorder.ondataavailable = (event) => {

                    this.chunks.push(event.data);

                    // Convert blob to base64
                    const reader = new FileReader();
                    reader.readAsDataURL(event.data);
                    reader.onloadend = () => {
                        const base64data = reader.result;

                        // Now you can send the base64data to WebSocket or anywhere else you want.
                        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                            this.socket.send(base64data);
                        }
                    };
                };


                this.recorder.onstop = async () => {
                    clearInterval(this.state.intervalId); // Clear the interval timer
                    const blob = new Blob(this.chunks, {type: 'audio/wav'});
                    this.state.audioURL = URL.createObjectURL(blob);
                    // console.log('Recording stopped. Saving the recording.');
                    //this.props.record.data[this.props.name] = this.state.audioURL;
                    await this.saveRecording(blob);

                    this.state.recording = false;
                    this.state.isRecording = false;
                    this.state.startTime = 0; // Reset the start time
                    this.state.currentTime = 0; // Reset the current time
                    this.state.pausetime = 0; // Reset the pause time
                    this.state.recordingStatus = 'inactive';
                };
                this.recorder.onstart = () => {
                    this.displayTimestamp(); // Assuming you have implemented this method
                    this.state.recording = true;
                    this.state.isRecording = true;
                    this.state.recordingStatus = 'recording';
                    // Initialize the total time paused and last pause timestamp
                    this.state.totalPausedTime = 0;
                    this.state.lastPauseTimestamp = 0;

                    this.state.intervalId = setInterval(() => {
                        // When recording is paused, store the timestamp of the pause start
                        if (this.state.recordingStatus === 'paused') {
                            if (this.state.lastPauseTimestamp === null) {
                                this.state.lastPauseTimestamp = Date.now();
                            }
                            return;
                        }

                        // If resuming from pause, update the total paused time and reset last pause timestamp
                        if (this.state.lastPauseTimestamp) {
                            this.state.totalPausedTime += Date.now() - this.state.lastPauseTimestamp;
                            this.state.lastPauseTimestamp = null;
                        }

                        // Calculate the current time minus the total paused duration
                        this.state.currentTime = (Date.now() - this.state.startTime - this.state.totalPausedTime) / 1000;

                        // Format the time
                        const minutes = Math.floor(this.state.currentTime / 60).toString().padStart(2, '0');
                        const seconds = Math.floor(this.state.currentTime % 60).toString().padStart(2, '0');
                        const millis = Math.floor((this.state.currentTime - Math.floor(this.state.currentTime)) * 1000).toString().padStart(3, '0');

                        // Update timestamp in UI

                        // Also update separate state parts for minutes, seconds, and milliseconds
                        this.state.currentTimeMinutes = minutes;
                        this.state.currentTimeSeconds = seconds;
                        this.state.currentTimeMilliseconds = millis;

                    }, 50); // Update 10 times per second for smoother UI updates/ Update every second
                };

                this.state.recordingStatus = 'recording';
                this.recorder.start(3000); // Set the timeslice to 2 seconds
                this.displayTimestamp();
                this.state.recording = true;
                this.state.isRecording = true;


                // Handle receiving of transcribed audio and update the transcript
                if (!this.transcriptions) {
                    //  console.error('Transcriptions object is not initialized.');
                    // this.transcriptions = {}; // Safely initialize it if not already done
                }
                this.transcriptions = {};

                this.socket.onmessage = (event) => {
                    try {
                        const response = JSON.parse(event.data);

                        if (response.type !== 'Results') {
                            // console.log("Ignoring non-'Results' message type.");
                            return;
                        }

                        const alternatives = response?.channel?.alternatives;
                        if (!alternatives || alternatives.length === 0 || !alternatives[0].words) {
                            // console.warn('Received unexpected message format or empty alternatives:', response);
                            return;
                        }

                        const words = alternatives[0].words;
                        const startTime = words[0]?.start;
                        const endTime = words[words.length - 1]?.end;
                        const transcript = alternatives[0]?.transcript;
                        const isFinal = response?.is_final;

                        if (startTime !== undefined && endTime !== undefined && transcript) {
                            const segmentKey = `${startTime}-${endTime}`;

                            if (isFinal) {
                                // Remove overlapping segments for final results
                                Object.keys(this.transcriptions).forEach((existingKey) => {
                                    const [existingStart, existingEnd] = existingKey.split('-').map(Number);
                                    if (existingStart >= startTime && existingEnd <= endTime) {
                                        delete this.transcriptions[existingKey];
                                    }
                                });
                            }

                            // Add or update the transcript segment
                            this.transcriptions[segmentKey] = transcript;

                            // Construct the full transcript by sorting the keys
                            const fullTranscript = Object.keys(this.transcriptions)
                                .sort((a, b) => parseFloat(a) - parseFloat(b))
                                .map((key) => this.transcriptions[key])
                                .join(' ')
                                .trim();

                            // Log the full transcript
                            //console.log('Full Transcript:', fullTranscript);

                            // Update the component's state with the new transcript
                            this.state.transcript = fullTranscript;
                            this.props.record.data.transcription_data = fullTranscript;


                            // const textarea = document.querySelector('textarea.wrr_custom_textarea');
                            //textarea.textContent = fullTranscript;
                            //if (textarea) {
                            //   textarea.scrollTop = textarea.scrollHeight;
                            //}
                            if (this.transcriptionsRef.el) {
                                this.transcriptionsRef.el.scrollTop = this.transcriptionsRef.el.scrollHeight;
                            }


                        } else {
                            // console.warn('Received message with missing start time or transcript:', response);
                        }
                    } catch (error) {
                        //  console.error('Error processing the WebSocket message:', error);
                    }
                };

            } catch (error) {
                //console.error('Error accessing microphone:', error);
            }
        }
    }

    recordVoiceWaveSurfer(state) {
        const saveButton = document.querySelector('button.o_form_button_save');

        this.displayTimestamp();

        if (this.state.recording) {
            this.recorder.stopRecording();
            this.state.recording = false;
            this.state.isRecording = false;
            // Close the WebSocket connection when recording stops
            if (this.socket) {
                this.socket.close();
                this.socket = null;
            }
        } else {
            // Construct WebSocket URL
            let wsProtocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
            let wsPort =
                location.port && parseInt(location.port, 10)
                    ? parseInt(location.port, 10) + 1000
                    : location.protocol === 'wss:'
                        ? 443
                        : 80;
            let wsPath = 'realtime_transcribe';

            if (wsPort === 443) {
                // Prefix the path with 'custom_socket' if the port is 443
                wsPath = 'custom_socket/' + wsPath;
            }
            if (wsPort === 80) {
                wsPort = ""
                // Prefix the path with 'custom_socket' if the port is 443
                wsPath = 'custom_socket/' + wsPath;
            }
            const languageQueryParam = `language=${encodeURIComponent(this.state.selectedLanguage)}`; // Include the selected language as a query parameter

            // console.log('languageQueryParam :', languageQueryParam)
            let wsAddress = `${wsProtocol}//${location.hostname}:${wsPort}/${wsPath}?${languageQueryParam}`;
            // Open a new WebSocket connection when recording starts
            this.socket = new WebSocket(wsAddress);

            // Connection opened
            this.socket.onopen = (event) => {
              this.socket.send(this.model);
            };
            this.socket.onclose = (event) => {
              console.log("The connection has been closed.", event);
            };
            this.socket.onerror = (event) => {
              console.log("The connection has been closed.", event);
            };

            try {
                this.state.startTime = Date.now(); // Start time of the recording
                this.state.currentTime = 0; // Current time of the recording
                this.state.intervalId = null; // ID of the interval timer

                this.state.recordingStatus = 'recording';

                // Get selected device
                const micSelect = document.querySelector('#mic-select');
                const deviceId = micSelect.value;
                this.recorder.startRecording({ deviceId });

                this.displayTimestamp();
                this.state.recording = true;
                this.state.isRecording = true;

                // Handle receiving of transcribed audio and update the transcript
                if (!this.transcriptions) {
                    //  console.error('Transcriptions object is not initialized.');
                    // this.transcriptions = {}; // Safely initialize it if not already done
                }
                this.transcriptions = {};

                this.socket.onmessage = (event) => {
                    try {
                    this.state.transcript += event.data + " ";
                        const response = JSON.parse(event.data);

                        if (response.type !== 'Results') {
                            // console.log("Ignoring non-'Results' message type.");
                            return;
                        }

                        const alternatives = response?.channel?.alternatives;
                        if (!alternatives || alternatives.length === 0 || !alternatives[0].words) {
                            // console.warn('Received unexpected message format or empty alternatives:', response);
                            return;
                        }

                        const words = alternatives[0].words;
                        const startTime = words[0]?.start;
                        const endTime = words[words.length - 1]?.end;
                        const transcript = alternatives[0]?.transcript;
                        const isFinal = response?.is_final;

                        if (startTime !== undefined && endTime !== undefined && transcript) {
                            const segmentKey = `${startTime}-${endTime}`;

                            if (isFinal) {
                                // Remove overlapping segments for final results
                                Object.keys(this.transcriptions).forEach((existingKey) => {
                                    const [existingStart, existingEnd] = existingKey.split('-').map(Number);
                                    if (existingStart >= startTime && existingEnd <= endTime) {
                                        delete this.transcriptions[existingKey];
                                    }
                                });
                            }

                            // Add or update the transcript segment
                            this.transcriptions[segmentKey] = transcript;

                            // Construct the full transcript by sorting the keys
                            const fullTranscript = Object.keys(this.transcriptions)
                                .sort((a, b) => parseFloat(a) - parseFloat(b))
                                .map((key) => this.transcriptions[key])
                                .join(' ')
                                .trim();

                            // Log the full transcript
                            // console.log('Full Transcript:', fullTranscript);

                            // Update the component's state with the new transcript
                            this.state.transcript = fullTranscript;
                            this.props.record.data.transcription_data = fullTranscript;


                            // const textarea = document.querySelector('textarea.wrr_custom_textarea');
                            //textarea.textContent = fullTranscript;
                            //if (textarea) {
                            //   textarea.scrollTop = textarea.scrollHeight;
                            //}
                            if (this.transcriptionsRef.el) {
                                this.transcriptionsRef.el.scrollTop = this.transcriptionsRef.el.scrollHeight;
                            }


                        } else {
                            // console.warn('Received message with missing start time or transcript:', response);
                        }
                    } catch (error) {
                        // console.error('Error processing the WebSocket message:', error);
                    }
                };

            } catch (error) {
                // console.error('Error accessing microphone:', error);
            }
        }
    }

    createAudio() {
        this.audio = new Audio(this.state.audioURL);
        this.audio.onended = () => {
            this.audio = null;
            this.state.audioPlaying = false;
            //this.stopVisualizer(); // Stop the visualizer when playback ends
        };
    }

    playRecording() {
        if (!this.audio) {
            this.createAudio();
        }

        if (! this.wavesurfer.isPlaying()) {
            this.wavesurfer.play();
            this.state.audioPlaying = true;
            // Display the timestamp
            this.displayTimestamp();
        } else  {
            this.pauseAudio();
        }
    }

    displayTimestamp() {
        const updateTimestamp = () => {
            if (this.audio && this.audio.currentTime !== undefined) {
                let currentTime = this.audio.currentTime;
                if (this.state.recordingStatus === 'recording') {
                    currentTime = this.state.currentTime;
                }

                const minutes = Math.floor(currentTime / 60).toString().padStart(2, '0');
                const seconds = Math.floor(currentTime % 60).toString().padStart(2, '0');
                const millis = Math.floor(currentTime % 1000).toString().padStart(3, '0');

                // Update the currentTime parts in the state
                this.state.currentTimeMinutes = minutes // .toString().padStart(2, '0');
                this.state.currentTimeSeconds = seconds //.toString().padStart(2, '0');
                if (this.state.recordingStatus === 'recording') {
                    this.state.currentTimeMilliseconds = millis //.toString().padStart(3, '0');
                } else {
                    this.state.currentTimeMilliseconds = "000" //.toString().padStart(3, '0');
                }
            }

            if (this.state.audioPlaying) {
                requestAnimationFrame(updateTimestamp);
            }
        };

        updateTimestamp();
    }

    pauseAudio() {
        if (this.audio) {
            this.wavesurfer.pause();
            this.state.audioPlaying = false;
        }
    }

    stopAudio() {
        if (this.audio) {
            this.wavesurfer.pause();
            if (this.audio.currentTime !== undefined) {
                this.audio.currentTime = 0; // Reset audio to the beginning
            }
            this.audio = null;
            this.state.audioPlaying = false;
        }
    }
    async changeModel(e) {
        let value = e.target.value;
        this.model = value;
        console.log('Model changed to:', value);
    }
    async startRecording() {
        if (this.recorder && this.recorder.isRecording()) {
            // Already recording, do nothing
            return;
        }

        if (this.recorder && this.recorder.isPaused()) {
            // If paused, resume recording instead
            this.resumeRecording();
            return;
        }
        this.state.recordingStatus = 'recording';

        // Initialize and start a new recording
        await this.recordVoiceWaveSurfer(); // Assumes recordVoice is a method that starts new recording
    }

    pauseRecording() {
        if (this.recorder && this.recorder.isRecording()) {
            this.recorder.pauseRecording();
            this.state.recordingStatus = 'paused';
        }
    }

    resumeRecording() {
        if (this.recorder && this.recorder.isPaused()) {
            this.recorder.resumeRecording();
            this.state.recordingStatus = 'recording';
        }
    }

    forwardAudio() {
        if (this.audio) {
            this.audio.currentTime += 15
        }
    }

    reverseAudio() {
        if (this.audio) {
            this.audio.currentTime -= 15
        }
    }

    restartAudio() {
        //    console.log('Restarting Audio');
        if (this.audio) {
            this.audio.currentTime = 0;
            this.audio.play();
        }
    }

    stopRecording2() {
        if (this.recorder && this.recorder.isRecording()) {
            // console.log('Stopping Recording');
            this.recorder.stop();
            this.gumStream.getAudioTracks()[0].stop();
            this.state.recording = false;
            this.state.isRecording = false;
        }
    }

    stopRecording() {
        // console.log('Stopping Recording...');
        if (this.recorder && (this.recorder.isRecording() || this.recorder.isPaused())) {
            this.recorder.stopRecording();

            this.state.isRecording = false;
            this.state.recording = false;
            this.state.isPaused = false;
            this.state.currentTime = '00:00';
            this.state.recordingStatus = 'inactive';
        }
    }

    async deleteRecordingOff() {
        if (
            !this.props.record ||
            !this.props.record.data ||
            !this.props.record.data.id
        ) {
            this.notification.add(_lt('Record does not exist or is not saved yet.'), {
                type: 'warning',
            });
            return;
        }


        const fieldName = this.props.name;
        const modelName = this.modelName;
        // console.log('deleteRecording called for record:', this.props.record);
        if (this.props.record && this.props.record.data) {
            const result = await this.rpc('/web/dataset/call_kw', {
                model: modelName,
                method: 'write',
                args: [[this.props.record.data.id], {
                    [fieldName]: null,
                    'transcription_data': '',
                    'corrected_transcription_data': ''
                }],
                kwargs: {},
            });
            // console.log('deleteRecording RPC response:', result);
            this.state.audioURL = null;
            this.state.audioPlaying = false;
            this.state.recording = false;
            this.state.hasRecording = false;
            this.state.transcript = '';
            this.props.record.data.transcription_data = '';
            this.state.transcribed = '';


        }
        this.resetState();
    }

    async deleteRecording() {
        if (
            !this.props.record ||
            !this.props.record.data ||
            !this.props.record.data.id
        ) {
            this.notification.add(_lt('Record does not exist or is not saved yet.'), {
                type: 'warning',
            });
            return;
        }

        const fieldName = this.props.name;
        const modelName = this.modelName;

        // Confirmation dialog
        let confirmed = await this.confirmDialog();
        if (confirmed) {
            // If confirmed, proceed with the deletion
            const result = await this.rpc('/web/dataset/call_kw', {
                model: modelName,
                method: 'write',
                args: [[this.props.record.data.id], {
                    [fieldName]: null,
                    'transcription_data': '',
                    'corrected_transcription_data': ''
                }],
                kwargs: {},
            });

            this.state.audioURL = null;
            this.state.audioPlaying = false;
            this.state.recording = false;
            this.state.hasRecording = false;
            this.state.transcript = '';
            this.props.record.data.transcription_data = '';
            this.state.transcribed = '';

            this.resetState();

            this.initWaveSurfer();
            this.initMicSelect();
        }
    }

    confirmDialog() {
        return new Promise((resolve) => {
            new Dialog(this, {
                title: _lt("Confirmation"),
                $content: $('<div>').append(_lt("<h1>Are you sure you want to delete this recording?</h1>")),

                size: 'medium',
                subtitle: _lt("Warning: This action cannot be undone."),


                buttons: [
                    {
                        text: _lt("Yes"),
                        classes: 'btn.btn-danger',
                        close: true,
                        click: () => resolve(true)
                    },
                    {
                        text: _lt("No"),
                        close: true,
                        click: () => resolve(false)
                    }
                ]
            }).open();
        });

    }

    // Create a waveform visualizer using the audio-visualizer canvas, and the audioContext and audioSource
    createPlayWaveSurfer() {
        if (! this.audio) this.createAudio();
        if (this.wavesurfer) this.wavesurfer.destroy();
        this.wavesurfer = window.WaveSurfer.create({
            container: this.waveformRef,
            height: this.waveformRef.offsetHeight,
            width: this.waveformRef.offsetWidth,
            media: this.audio,
            splitChannels: false,
            normalize: false,
            waveColor: '#0E6DA1',
            progressColor: '#E7F0F6',
            cursorColor: '#000000',
            cursorWidth: 2,
            barWidth: 2,
            barGap: 2,
            barRadius: 3,
            barHeight: 1.2,
            barAlign: '',
            mediaControls: true,
            autoplay: false,
            dragToSeek: true,
            hideScrollbar: true,
        });
        this.wavesurfer.on("ready", () => {
            this.state.totalDuration = this.wavesurfer.getDuration();
        });
        this.wavesurfer.on('timeupdate', (currentTime) => {
            const totalSeconds = Math.floor(currentTime);
            const minutes = Math.floor(totalSeconds / 60);
            const seconds = Math.floor(totalSeconds % 60);
            const millis = Math.floor((currentTime - totalSeconds) * 1000); // Get the milliseconds part

            // Update the currentTime parts in the state
            this.state.currentTimeMinutes = minutes.toString().padStart(2, '0');
            this.state.currentTimeSeconds = seconds.toString().padStart(2, '0');
            this.state.currentTimeMilliseconds = millis.toString().padStart(3, '0');
        });
    }

    initWaveSurfer() {
        // Create an instance of WaveSurfer
        if (this.wavesurfer) {
            this.wavesurfer.destroy();
        }

        let scrollingWaveform = true

        this.wavesurfer = window.WaveSurfer.create({
            container: this.waveformRef,
            height: this.waveformRef.offsetHeight,
            width: this.waveformRef.offsetWidth,
            splitChannels: false,
            normalize: false,
            waveColor: '#0E6DA1',
            progressColor: '#E7F0F6',
            cursorColor: '#000000',
            cursorWidth: 2,
            barWidth: 2,
            barGap: 2,
            barRadius: 3,
            barHeight: 1.2,
            barAlign: '',
            mediaControls: false,
            autoplay: false,
            dragToSeek: true,
            hideScrollbar: true,
        });

        this.recorder = this.wavesurfer.registerPlugin(window.WaveSurfer.Record.create({ scrollingWaveform, renderRecordedAudio: false }));

        // Initialize the chunks array here
        this.chunks = [];

        this.recorder.on('record-start', () => {
            this.updateProgress();
            this.state.intervalChunkId =  setInterval(() => {
                // Code to execute every 2 seconds
                if (! this.recorder.isPaused()) {
                    this.recorder.pauseRecording();
                    this.recorder.resumeRecording();
                }
            }, 2000);
        });

        this.recorder.on('record-progress', (time) => {
            // console.log('Recording progress:', time);
        });

        this.recorder.on('record-pause', (blob) => {
            //console.log('Blob:', blob);
            const blob2 = blob.slice(this.blobBytes);
            this.blobBytes = blob.size;
            //console.log('Blob2:', blob2);
            this.chunks.push(blob2);
            // Convert blob to base64
            const reader = new FileReader();
            reader.readAsDataURL(blob2);
            reader.onloadend = () => {
                const base64data = reader.result;
                if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                    //console.log('Sending to socket...');
                    this.socket.send(base64data);
                }
            };
        });

        // Render recorded audio
        this.recorder.on('record-end', async (blob) => {
            clearInterval(this.state.intervalId); // Clear the interval timer
            clearInterval(this.state.intervalChunkId);
            this.state.audioURL = URL.createObjectURL(blob);
            this.state.hasRecording = true;

            this.state.recording = false;
            this.state.isRecording = false;
            this.state.startTime = 0; // Reset the start time
            this.state.currentTime = 0; // Reset the current time
            this.state.pausetime = 0; // Reset the pause time
            this.state.recordingStatus = 'inactive';

            this.createPlayWaveSurfer();

            await this.saveRecording(blob);
        });
    }

    updateProgress() {
        this.displayTimestamp();
        this.state.recording = true;
        this.state.isRecording = true;
        this.state.recordingStatus = 'recording';
        // Initialize the total time paused and last pause timestamp
        this.state.totalPausedTime = 0;
        this.state.lastPauseTimestamp = 0;

        this.state.intervalId = setInterval(() => {
            // When recording is paused, store the timestamp of the pause start
            if (this.state.recordingStatus === 'paused') {
                if (this.state.lastPauseTimestamp === null) {
                    this.state.lastPauseTimestamp = Date.now();
                }
                return;
            }

            // If resuming from pause, update the total paused time and reset last pause timestamp
            if (this.state.lastPauseTimestamp) {
                this.state.totalPausedTime += Date.now() - this.state.lastPauseTimestamp;
                this.state.lastPauseTimestamp = null;
            }

            // Calculate the current time minus the total paused duration
            this.state.currentTime = (Date.now() - this.state.startTime - this.state.totalPausedTime) / 1000;

            // Format the time
            const minutes = Math.floor(this.state.currentTime / 60).toString().padStart(2, '0');
            const seconds = Math.floor(this.state.currentTime % 60).toString().padStart(2, '0');
            const millis = Math.floor((this.state.currentTime - Math.floor(this.state.currentTime)) * 1000).toString().padStart(3, '0');

            // Update timestamp in UI

            // Also update separate state parts for minutes, seconds, and milliseconds
            this.state.currentTimeMinutes = minutes;
            this.state.currentTimeSeconds = seconds;
            this.state.currentTimeMilliseconds = millis;

        }, 50); // Update 10 times per second for smoother UI updates/ Update every second
    }

    initMicSelect() {
        const micSelect = document.querySelector('#mic-select');
        if (micSelect) {
            // Mic selection
            window.WaveSurfer.Record.getAvailableAudioDevices().then((devices) => {
                devices.forEach((device) => {
                    const option = document.createElement('option');
                    option.value = device.deviceId;
                    option.text = device.label || device.deviceId;
                    micSelect.appendChild(option)
                });
            });
        }
    }

    updateVisualizerDuringPlayback() {
        const visualizerCanvas = document.getElementById('audio-visualizer');
        if (!visualizerCanvas) return; // Ensure the canvas element is found
        const visualizerCanvasContext = visualizerCanvas.getContext('2d');
        const audioSource = this.audioContext.createMediaElementSource(this.audio);
        const analyzer = this.audioContext.createAnalyser();
        audioSource.connect(analyzer);
        analyzer.connect(this.audioContext.destination);

        const dataArray = new Uint8Array(analyzer.frequencyBinCount);
        const canvasWidth = visualizerCanvas.width;
        const canvasHeight = visualizerCanvas.height;

        const gradient = visualizerCanvasContext.createLinearGradient(0, 0, 0, canvasHeight);
        gradient.addColorStop(0, 'rgba(35, 7, 77, 1)');
        gradient.addColorStop(1, 'rgba(204, 83, 51, 1)');

        const drawVisualizer = () => {
            analyzer.getByteFrequencyData(dataArray);

            visualizerCanvasContext.clearRect(0, 0, canvasWidth, canvasHeight);
            const barWidth = (canvasWidth / dataArray.length) * 2.5;
            let barHeight;
            let x = 0;

            for (let i = 0; i < dataArray.length; i++) {
                barHeight = dataArray[i] / 2;
                visualizerCanvasContext.fillStyle = gradient;
                visualizerCanvasContext.fillRect(x, canvasHeight - barHeight, barWidth, barHeight);

                x += barWidth + 1;
            }

            if (this.state.audioPlaying) {
                requestAnimationFrame(drawVisualizer);
            }
        };

        drawVisualizer();
    }

    clickGenerateReport() {
        // Find the button by its name attribute
        const button = window.document.getElementsByName('action_generate_report_threading')[0];

        // Check if the button exists
        if (button) {
            // Click the button
            button.click();
            //  console.log('Generate Report button clicked.');
        } else {
            // Log an error or handle the absence of the button
            // console.error('Generate Report button not found.');
        }
    }

    clickTranscribe() {
        // Find the button by its name attribute
        const button = window.document.getElementsByName('action_voice_record_transcribe')[0];

        // Check if the button exists
        if (button) {
            // Click the button
            button.click();

        } else {
            // Log an error or handle the absence of the button

        }
    }

    clickCorrectTranscription() {
        // Find the button by its name attribute
        const button = window.document.getElementsByName('action_voice_record_correct_transcript')[0];

        // Check if the button exists
        if (button) {
            // Click the button
            button.click();

        } else {
            // Log an error or handle the absence of the button

        }
    }

    correct_transcript_render() {
        const container = this.containerRef.el;
        if (container) {
            container.innerHTML = this.state.correct_transcript || "";
        }
    }
}

VoiceRecorder.template = 'wrrrit_ai.VoiceRecorder';
VoiceRecorder.props = {
    ...standardFieldProps,
    model: {type: String, optional: true},
    voice: {type: String, optional: true},
    transcription: {type: String, optional: true},
};
VoiceRecorder.extractProps = ({attrs}) => {
    return {
        model: attrs.options.model,
        voice: attrs.options.voice,
        transcription: attrs.options.transcription,
    };
};

VoiceRecorder.supportedTypes = ['binary'];
registry.category('fields').add('wrrrit_recorder', VoiceRecorder);
export default VoiceRecorder;
