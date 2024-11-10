from fasthtml.common import *
from assistants import *
import anthropic
import os

speech_to_text_js = """
// Check if browser supports speech recognition
if (!('SpeechRecognition' in window) && !('webkitSpeechRecognition' in window)) {
    alert('Your browser does not support speech recognition. Please try a different browser.');
}

let recognition;
let transcription = '';

function startRecording() {
    recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    recognition.lang = 'en-US';
    recognition.interimResults = true;
    recognition.continuous = true;

    recognition.onresult = (event) => {
        const result = event.results[event.results.length - 1];
        const transcript = result[0].transcript;
        if (result.isFinal) {
            transcription += transcript + ' ';
            updateTranscriptionArea();
        } else {
            // Update with interim results
            updateTranscriptionArea(transcript);
        }
    };

    recognition.onerror = (event) => {
        console.error('Speech recognition error', event.error);
        stopRecording();
    };

    recognition.start();
    me('#recordBtn').textContent = 'Stop';
}

function stopRecording() {
    if (recognition) {
        recognition.stop();
        me('#recordBtn').textContent = 'Record';
    }
}

function updateTranscriptionArea(interimTranscript = '') {
    me('#transcriptionArea').value = transcription + interimTranscript;
}

me('#recordBtn').on('click', () => {
    const button = me('#recordBtn');
    if (button.textContent === 'Record') {
        startRecording();
    } else {
        stopRecording();
    }
});

me('#clearTranscription').on('click', () => {
    transcription = '';
    updateTranscriptionArea();
});

me('#clearFormatted').on('click', () => {
    me('#formattedNotes').value = '';
});

htmx.on("htmx:afterSettle", (event) => {
    if (event.detail.target && event.detail.target.id === "formattedNotes") {
        const formattedNotesArea = me('#formattedNotes');
        if (formattedNotesArea) {
            formattedNotesArea.value = event.detail.target.textContent;
        }
    }
});

me('#copyFormatted').on('click', () => {
    const formattedText = me('#formattedNotes').value;
    navigator.clipboard.writeText(formattedText).then(() => {
        alert('Formatted notes copied to clipboard!');
    });
});

me('#emailFormatted').on('click', () => {
    const formattedText = me('#formattedNotes').value;
    const subject = 'Formatted Transcription Notes';
    const mailtoLink = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(formattedText)}`;
    window.location.href = mailtoLink;
});
"""

custom_css = """
:root { --primary: #0055b7; --secondary: #e6e6e6; --text: #333333; --white: #ffffff; --accent: #ff4c4c; }
body { font-family: 'Helvetica Neue', Arial, sans-serif; color: var(--text); background-color: var(--white); line-height: 1.6; margin: 0; padding: 0; }
.container { max-width: 800px; margin: 0 auto; padding: 2rem; }
h1, h2, h3, h4, h5, h6 { margin-top: 2rem; margin-bottom: 1rem; font-weight: bold; }
h1 { font-size: 2.5rem; }
h2 { font-size: 2rem; text-transform: uppercase; letter-spacing: 0.1em; }
button, select, textarea { width: 100%; margin-bottom: 15px; padding: 0.7rem; border: 1px solid var(--secondary); font-size: 1rem; }
button { background-color: var(--primary); color: var(--white); border: none; cursor: pointer; text-transform: uppercase; letter-spacing: 0.1em; transition: background-color 0.3s ease; }
button:hover, button:focus { background-color: var(--text); }
#recordBtn { display: flex; align-items: center; justify-content: center; }
#recordBtn::before { content: '🎙️'; margin-right: 10px; }
.button-group { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 1rem; }
#transcriptionArea, #formattedNotes { height: 200px; resize: vertical; }
@media screen and (min-width: 768px) { .button-group { flex-direction: row; } button { width: auto; } }
.htmx-indicator{ opacity:0; transition: opacity 500ms ease-in; display: inline-block;}
.htmx-request .htmx-indicator{ opacity:1; margin-left: 1rem; width: 24px; height: 24px; }
"""

app, rt = fast_app(
    pico=False,  # Disable Pico CSS as we're using our own styles
    hdrs=(Style(custom_css),),
    static_path=os.getcwd(),
)

@rt('/')
def get():
    return Titled("Write My Notes",
        Container(
            Div(Button("Record", _id="recordBtn")),
            Form(
                Div(
                    Textarea(_id="transcriptionArea", name="transcriptionArea", placeholder="Your transcription shows here"),
                    Button("Clear", _id="clearTranscription", type="button")
                ),
                Div(
                    Select(
                        Option("Select note type:", value="", disabled=True, selected=True),
                        Option("Patient Letter", value="patient_assistant"),
                        Option("GP Letter 1", value="gp_assistant_1"),
                        Option("GP Letter 2", value="gp_assistant_2"),
                        Option("SBAR Note", value="sbard_assistant"),
                        Option("Custom Note", value="custom_assistant"),
                        _id="assistantSelector",
                        name="assistant",
                        hx_post="/handle_selection",
                        hx_target="#customOptions",
                        hx_trigger="change",
                    )
                ),
                Div(_id="customOptions"),
                Div(
                    Button("Submit", _id="submit", 
                           type="submit",
                           hx_post="/submit",
                           hx_target="#formattedNotes",
                           hx_indicator="#spinner"),
                    Img(id="spinner", cls="htmx-indicator", src="bars.svg", alt="Loading...")
                ),
                _id="noteForm"
            ),
            Div(Textarea(_id="formattedNotes", placeholder="Formatted notes here..")),
            Div(
                Button("Clear", _id="clearFormatted", type="button"),
                Button("Copy", _id="copyFormatted", type="button"),
                Button("Email", _id="emailFormatted", type="button"),
                cls="button-group"
            ),
            Script(speech_to_text_js)
        )
    )

assistants = {
    "patient_assistant": patient_assistant,
    "gp_assistant_1": gp_assistant_1,
    "gp_assistant_2": gp_assistant_2,
    "sbard_assistant": sbard_assistant,
    "custom_assistant": custom_assistant,
}

sections = [
    "Chief Complaint", "History of Present Illness (HPI)", 
    "Past Psychiatric History", "Medical History", "Family History", 
    "Social History", "Developmental History", 
    "Mental Status Examination (MSE)", "Risk Assessment", 
    "Formulation", "Diagnosis", "Treatment Plan"
]

checkbox_grid = Div(
    *(Label(
        Input(type="checkbox", name="sections", value=section),
        section.split('(')[0].strip(),)
        for section in sections),
        )

@rt("/handle_selection")
def post(assistant:str):
    if assistant == "custom_assistant":
        return checkbox_grid
    else:
        return ""

from dotenv import load_dotenv
load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

def get_claude_completion(clinical_notes, assistant, model="claude-3-haiku-20240307"):
    message = client.messages.create(
        model=model,
        max_tokens=1000,
        temperature=0,
        messages=[ { "role": "user", "content": [ { "type": "text", "text": assistant(clinical_notes), } ] } ])
    return message.content[0].text

@rt("/submit")
def post(transcriptionArea: str, assistant:str, sections: list=None, writing_style: str=None):
    result = get_claude_completion(transcriptionArea, assistants[assistant])
    return result

serve()