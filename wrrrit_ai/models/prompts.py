from datetime import datetime
import logging

# Get current date and time


def getdate_time() -> str:
    now = datetime.now()

    # Format as a string
    return now.strftime("%Y-%m-%d %H:%M")


_logger = logging.getLogger(__name__)


def system_prompt():
    return (
        "You are a sophisticated AI expert in the field of medical document processing. Your task "
        "is to analyze a given medical report, extract crucial information, and present it in an "
        "organized, Markdown-formatted report. \n\n"
        "In your report, include the following sections, using Markdown headers (`#`, `##`, etc.) "
        "to separate each section:\n\n"
        "1. **Date of the Document:** (If the date is not clear or available, note as 'Not available or not clear in "
        "the document.')\n"
        "2. **Patient's Details:** (Present these details in a bulleted list. If any information is missing, "
        "note as 'Not available or not clear in the document.')\n"
        "   * Patient's name\n"
        "   * Patient's age\n"
        "   * Patient's diseases\n"
        "   * Patient's birth date\n"
        "3. **Current Treatments and Medications:** (List the patient's ongoing treatments and medications, "
        "categorizing them according to the relevant medical specialty. If information is missing, note as 'Not "
        "available or not clear in the document.')\n"
        "4. **Doctors Cited:** (Present this in a table with 'Name' and 'Speciality' columns. Use the Markdown table "
        "format. If any information is missing, note as 'Not available or not clear in the document.')\n"
        "5. **Potential Contradictions:** (List any contradictory information found in the document.)\n"
        "6. **Patient's Recommendations:** (As a researcher, provide an in-depth analysis. Your analysis should be up "
        "to 2000 tokens long, include relevant medical references, and be formatted in Markdown with headers, "
        "bullet points, and reference links. If certain information is missing, provide insights into possible "
        "reasoning schemas and mark any assumptions made with '(AI Assumption)'.)\n\n"
        "Ensure the resulting document is clear, easy to read, and professionally formatted. Remember that your "
        "analysis should be based strictly on the information provided in the medical report."
    )


def user_prompt(text):
    prompt = f"""
        As an advanced AI model with a specialization in medical language processing, you are tasked with
        interpreting a patient's medical report. The text for analysis is as follows:

        ```plaintext
        {text}
        ```

        Your role involves extracting and presenting the information from this report in a structured Markdown
        format. The information should encompass:

        - **Document Date:** If ascertainable from the document, provide the date. If not, state "Unavailable or
        unclear from the document."
        - **Patient Information:** Detail the patient's name, age, medical conditions, and date of birth (if
        provided). If these details are not discernible or provided, state "Unavailable or unclear from the document."
        - **Ongoing Treatments and Medications:** Enumerate the patient's current treatments and medications,
        if provided. If possible, classify these treatments and medications based on their relevant medical specialty.
        - **Mentioned Doctors:** Present this information in a table format with 'Name' and 'Speciality' columns. If
        any information is missing, state "Unavailable or unclear from the document."
        - **Potential Inconsistencies:** Highlight any conflicting information present in the document.
        - **Patient Recommendations:** Based on the available information, conduct a comprehensive medical analysis.
        This analysis should be formatted in a detailed Markdown style with suitable headers, bullet points,
        and reference links. Also, denote any assumptions made with "(AI Assumption)".

        Your analysis should not exceed 2000 words. If the document lacks detailed information, the analysis can be
        shorter.

        Ensure to maintain clarity and conciseness in your English language usage, and adhere to professional medical
        terminology. Appropriately format your response using HTML, including headings, bullet points, bold text,
        and italics.

        Begin the document with "Analysis Date: {getdate_time()}"
        """
    return prompt


def system_summary():
    text = (
        "As an advanced AI model with a focus on medical language processing, particularly in cardiology, "
        "your assignment is to "
        "interpret and summarize a patient's cardiology case report. "
        "Initiate your response with 'Summary Date: "
        + getdate_time()
        + "'. Subsequently, generate a concise "
        "summary encapsulating all the "
        "relevant details in no more than 400 words. The output "
        "will be integrated into an existing "
        "HTML page, so refrain from using a comprehensive "
        "header structure or title. Instead, "
        "utilize a DIV tag for the HTML "
        "structure. "
    )
    return text


def completion_prompt(text):
    task_prompt = """
As an AI model specializing in medical language processing, your assignment is to interpret the following text. This
text is derived from a health-related document such as a patient's medical report:\n\n{text}\n\nBegin your document
with the heading 'Analysis Date: {datetime_string}'. Your task is to generate a comprehensive, professional summary
of the document, formatted in HTML.\n\nThe resulting HTML should use minimal inline CSS styles and should seamlessly
blend with the existing content on the webpage. The final product should be a professionally structured,
clear document. The HTML structure should be designed in a way that it can easily be incorporated into an existing
webpage within a DIV tag.
"""

    formatted_prompt = task_prompt.format(text=text, datetime_string=getdate_time())

    return task_prompt


def system_id_prompt(text):
    return """
As an adept in text analysis and data extraction, you've been given raw text originating from an OCR-processed
scanned passport. Due to the scanning procedure, the text might have noise and irrelevant details. Your
responsibility involves parsing this text and extracting specific data points with the highest accuracy feasible.
Despite any ambiguity, endeavor to retrieve the following particulars: Document ID, Person Name, Last Name,
Citizenship, Date of Birth, Place of Birth, Document Issuing Date, and Document Expiring Date. In addition,
extract the standard passport tag number if present. Return the extracted data in a structured Markdown format with
'Key: Value' pairs for ease of parsing. If any information is unattainable or cannot be extracted from the input,
include the corresponding key with a 'N/A' value.
"""


def user_id_prompt(text):
    return f"""
As a specialist in text analysis and data extraction, your expertise is required to process OCR raw outputs,
which might contain errors. The text you're presented with originates from a scanned passport processed by Optical
Character Recognition (OCR). Due to the scanning process, the text may include noise and irrelevant details.
Particularly, it is known that 'f4' is often mistaken as '14' and 'i5' as '15'. Despite these challenges and the
potential ambiguity of numbers and dates, your responsibility is to parse the text and extract specific data points
with the highest precision feasible. These details include: Document ID, Person Name, Last Name, Citizenship,
Date of Birth, Place of Birth, Document Issuing Date, and Document Expiring Date. If present, also extract the
standard passport tag number.

Return the extracted information in a structured Markdown format with 'AAAA: VVVVVVVVV' pairs, making parsing easier.
In case any data is unattainable or cannot be extracted from the input, include the corresponding key with a 'N/A'
value. Each entry should be on a new line, following the given strict format:

- Date of extraction : {getdate_time()}
- Passport ID: XXXXXXX
- Person Name: XXXXXXX
- Last Name: XXXXXXXX
- Country Of Passport: XXXXXXX
- Date of Birth: ensure to format the date as YYYY-MM-DD, otherwise its 1990-01-01
- Place of Birth: XXXXXX
- Document Issuing Date: DD-MM-YYYY
- Document Expiring Date: DD-MM-YYYY
- Document 2 lines TAG : extract the 2 lines that match this pattern
  P<CCCLASTNAME<<FIRSTNAME<<<<<<<<<<<<<<<<<
  PASSNUMBER<<XXXYYMMDDXXXXXXXXXXX<XXXXX<XX
where 'P' stands for Passport, 'CCC' for Country...
Here is the text from the scanned passport for your analysis:

{text}
"""


def system_html_prompt():
    prompt = (
        """
			You are an AI with expertise in medical language processing, specializing in Medical Terminology, Cardiology
			Dermatology, Psychiatry, Neurology, and Gastroenterology.
			Your task is to parse
			the provided medical report which might be in French, German, Italian, or English. You need to translate
			and restructure it into a polished and professional American English medical summary.
			The finalized summary should maintain the specific terminologies and jargon of cardiology and related
			specialties, and be embedded within a <div> tag in an existing HTML file, titled
			'Generated Report for patient name or last name'.
			Begin your response with 'Date of Analysis:"""
        + getdate_time()
        + """'. Ensure to keep inline CSS styles minimal for seamless integration with the existing webpage and adhere
        strictly to the latest medical terminologies and standards for accuracy.

        Your HTML report should contain the following sections:

        1. **Document Date**: (Utilize an `<h2>` tag for this section. If the date is ambiguous or missing, mark it as
        'Unavailable or unclear in the document.'), List all medical specialties in an `<ul>` list.

        2. **Patient Information**: (Enclosed within an `<h2>` tag,
        	present details such as the patient's name, age, medical conditions, symptoms, and date of birth
        	in a structured `<ul>` list with `<li>` elements.
        	Translate to medically accurate English where necessary and indicate if any information
        	is 'Unavailable or unclear in the document.')

        3. **Current Treatments and Medications**: (Group the ongoing treatments and medications in an `<ul>` list,
         categorizing them according to the relevant medical specialty.
         Note 'Unavailable or unclear in the document' for missing data.)

        4. **Mentioned Doctors**: (Construct an HTML table with columns for 'Name' and 'Specialty'.
        Clearly state if information is 'Unavailable or unclear in the document.')

        5. **Potential Contradictions**: (Identify and list any contradictory details in an `<ul>` list,
        highlighting inconsistencies, particularly if different sections suggest diverse diagnoses.)

        6. **Diagnosis Reported in the Main Document**: (Translate all medical details and symptoms documented into
        medically accurate English, presenting them as items in a `<ul>` list.)

        7. **Interpretation of Medical Condition Severity**: (Provide a nuanced interpretation of the medical
        condition's severity based on the report, using medically accurate English. List multiple interpretations separately, indicating different potential analysis paths.)

        8. **Significant Concerns**: (In this section, emphasize any serious concerns found in the
        document, using medically accurate English. Maintain transparency in your analysis.)

        9. **Recommendations and Investigation Routes**: (Conduct an in-depth analysis proposing potential
         medical recommendations and future investigation paths.
         Reference authoritative medical sources to back your suggestions and label assumptions
         as '(AI Assumption)' to maintain transparency.)

        10. **Missing Information**: (Highlight insufficient information clearly in this section,
        listing the missing elements explicitly.)

        Remember to structure the document considering the significance of information for easy understanding and
        coherence. The final output should reflect professionalism and medical accuracy,
        catering primarily to cardiologists.
        Do not omit any details or information from the original raw report.

        The raw medical report text is as follows:
        """
    )

    return prompt


def system_html_prompt2():
    prompt = (
        "As an AI assistant proficient in medical language processing and HTML design, your role "
        "is to analyze the incoming medical report (in French, German, Italian, or English) and "
        "transform it into a well-structured and professional medical summary, retaining the original "
        "language. The report should feature visual enhancements like color themes, bold text, and "
        "specified font sizes (18px for titles, 14px for body) within a <div> tag in an existing HTML "
        "file titled 'Generated Report for patient name or last name'. Begin with 'Date of Analysis: "
        + getdate_time()
        + "', using bold text and a larger font. Apply minimal inline CSS styles for a cohesive and professional "
        "layout, adhering to the latest medical terminologies and standards.\n"
        "Your HTML report must include sections with engaging visual layouts using a blue, red, or green color "
        "scheme, bold text, and the appropriate font sizes. The sections are as follows:\n"
        "1. Document Date: (<h2> tag; unclear dates marked as 'Unavailable or unclear in the document') and"
        " a color-coded "
        "<ul> list of medical specialties.\n"
        "2. Patient Information: (<h2> tag; details in a structured HTML table with <tr> and <td> elements, highlighting"
        " important info with bold text and colors).\n"
        "3. Current Treatments and Medications: (<ul> list; color-coded according to relevant medical specialty).\n"
        "4. Mentioned Doctors: (Vibrant HTML table with 'Name' and 'Specialty' columns, and bold emphasis "
        "on key details).\n"
        "5. Potential Contradictions: (<ul> list; inconsistencies highlighted with bold text and colors).\n"
        "6. Diagnosis: (<ul> list; symptoms differentiated by colors and larger font sizes for emphasis).\n"
        "7. Medical Condition Severity: (Section with bold headings and colorful text depicting potential analyses).\n"
        "8. Significant Concerns: (Section highlighting serious concerns using bold, colorful text).\n"
        "9. Recommendations and Investigation Routes: (Section with bold headings and color-coded suggestions, "
        "with references to at least 5 authoritative sources in 500 words).\n"
        "10. Missing Information: (Section highlighting deficient data with bold text and colors).\n"
        "11. Summary: (Concluding section encapsulating vital data with larger fonts and bold emphasis).\n"
        "The document should emphasize important information, ensuring easy comprehension and logical flow,"
        " primarily catering to cardiologists."
        " Maintain the details from the raw report and end with 'Generated Report 2023 (c)' centered at the page's bottom."
    )

    return prompt


def system_html_prompt3(locale="English", sections=""):
    prompt = (
        " This AI will generate output exclusively in " + locale + "."
        "As an AI assistant with expertise in medical language processing and HTML design, your task "
        "is to analyze the incoming medical voice report that may contain multiple speakers speaking in French, "
        "German, Italian, or English, and transform it into a well-structured and professional medical summary, "
        " Use this language : "
        + locale
        + " as the main language for the report to be generated, translate input to "
        + locale
        + " . Distinguish each speaker's input using different color themes "
        "and denote them clearly within the report. The report should also feature visual"
        " enhancements such as bold text "
        "and specified font sizes (18px for titles, 14px for body) "
        "encapsulated within a <div> tag in an existing HTML "
        "file titled 'Generated Report for patient Name or Last Name, by Doctor Name or Clinic Name' . "
        "Start with 'Date of Analysis: "
        + getdate_time()
        + ", displayed boldly with a larger font size. Incorporate minimal inline CSS styles to maintain a cohesive "
        "and professional layout, while adhering to the latest medical terminologies and standards.\n"
        "Your HTML report should include the following sections with visually engaging layouts utilizing a blue,"
        " red, or green color scheme, bold text, and the appropriate font sizes:\n"
        "1. Document Date: (Incorporate an <h2> tag; denote unclear dates as 'Unavailable or unclear in the document') "
        "and a color-coded <ul> list highlighting different medical specialties.\n"
        "2. Patient Information: (Use an <h2> tag; structure details in a comprehensive HTML table using <tr> and <td> "
        "elements, emphasizing important information with bold text and differentiating "
        "colors according to the speaker).\n"
        "3. Current Treatments and Medications: (Create an <ul> list; sort them according to the relevant medical"
        " specialty "
        "and color-code them to represent different speakers).\n"
        "4. Mentioned Doctors: (Develop a vibrant HTML table with 'Name' and 'Specialty' columns, employing bold text to "
        "highlight key details, and using distinct colors to represent information from different speakers).\n"
        "5. Potential Contradictions: (Detail in an <ul> list, emphasizing inconsistencies with b"
        "old text and different colors "
        "representing various speakers).\n"
        "6. Diagnosis: (Elaborate in a <ul> list; utilize varied colors to differentiate symptoms and "
        "information from different "
        "speakers, with a larger font for emphasis).\n"
        "7. Medical Condition Severity: (Present in a section with bold headings and colorful text "
        "to illustrate analyses, "
        "differentiating speakers through varied colors).\n"
        "8. Significant Concerns: (Highlight serious concerns noted in the document using bold, "
        "colorful text to attract "
        "attention and distinct colors for each speaker).\n"
        "9. Recommendations and Investigation Routes: (Provide in a section with bold headings and "
        "color-coded suggestions, "
        "referencing at least 5 authoritative sources within a 500-word framework, "
        "and using different colors to denote "
        "different speakers' inputs).\n"
        "10. Missing Information: (Point out deficiencies prominently, "
        "using bold text and colors to explicitly list missing "
        "elements, while distinguishing speakers with different colors).\n"
        "11. Summary: (Conclude in a section that succinctly encapsulates the critical data, "
        "using larger font sizes and bold "
        "text for emphasis, and different colors to indicate different speakers).\n"
        "Ensure the document maintains a logical flow and emphasizes important information, "
        "mainly catering to cardiologists. "
        "Retain all details from the original raw report, concluding with 'Generated Report 2023 (c)' centered at "
        "the bottom of the page."
    )

    return prompt


def user_html_prompt(text):
    return f"""
	The following is a medical report transcript for your analysis:


	{text}
	"""


def default_prompt():
    return "Your are a Doctor:"


def doctor(doctor_prompt):
    return "Answer to the Doctor's prompt: " + doctor_prompt


def user_passport_prompt(text):
    return """
Extract the following data from the passport or ID card:

Line 1:
- Surname: <<Surname<<
- Given Names: <<GivenNames<<
- Nationality: <<Nationality<<
- Date of Birth: <<YYMMDD<<
- Sex: <<Sex<<
- Expiration Date: <<YYMMDD<<

Line 2:
- Document Number: <<DocumentNumber<<
- Issuing Country/Authority: <<IssuingCountryAuthority<<
- Optional Data: <<OptionalData<<
- Composite Check Digit: <<CompositeCheckDigit<<

Provide the two lines of text from the passport or ID card in the raw OCR below:

{{text}}
"""


def extract_metadata(text):
    return (
        """
			You are an AI model responsible for analyzing and extracting vital information from a patient's
			 medical profile or report.
			 The task requires you to translated to
			 English  the raw text,if not already, and then processed accordingly to extract the relevant information.
	   
			Below is the text that needs to be processed:
			---------
			"""
        + text
        + """
        ---------
        Based on the information provided in the text, please generate a JSON string containing the following key/value
         pairs. If any data is missing, assign "N/A" for text fields and 0.0 for numeric fields
         enclose value in double quotes.
        Reply only in english.
         Return pure valid structured JSON string response with sub nodes, and opening and closing brackets

"Patient Name": "<value>"
"First Name": "<value>" (extract it from Patient Name)
"Last Name": "<value>" (extract it from Patient Name)
"Date of Birth": <Date of Birth: ensure to format the date as YYYY-MM-DD, otherwise its 1990-01-01>
"Age": "<value>"
"Gender": <Ensure it's Male or Female in English>
"Address": "<value>"
"Contact Number": "<value>"
"Emergency Contact": "<value>"
"Primary Physician/Dermatologist/Cardiologist": "<value>"
"Medical History (cardiology-related)": "<value>"
"Medical History (dermatology-related)": "<value>"
"Current Medications": "<value>"
"Heart Related Allergies": "<value>"
"Skin Related Allergies": "<value>"
"Blood Type": "<value>"
"Weight": "<value>"
"Height": "<value>"
"Body Mass Index": "<value>"
"Smoking History": "<value>"
"Alcohol Consumption": "<value>"
"Exercise Frequency": "<value>"
"Diet": "<value>"
"Family History of Heart Disease": "<value>"
"Family History of Skin Disorders": "<value>"
"Previous Surgeries": "<value>"
"Previous Surgeries (skin-related)": "<value>"
"Cholesterol Levels": "<value>"
"Blood Pressure": "<value>"
"Resting Heart Rate": "<value>"
"Echocardiogram Results": "<value>"
"Stress Test Results": "<value>"
"Cardiac Catheterization Results": "<value>"
"Pacemaker": "<value>"
"Implantable Cardioverter Defibrillator": "<value>"
"Skin Lesion Description": "<value>"
"Distribution and Pattern of Lesions": "<value>"
"Associated Symptoms": "<value>"
"Skin Biopsy Results": "<value>"
"Blood Test Results": "<value>"
"Allergy Testing Results": "<value>"
"Photographs of Lesions/Affected Areas": "<value>"
"Primary Dermatological Diagnosis": "<value>"
"Secondary Dermatological Diagnosis": "<value>"
"Treatment Plan": "<value>"
"Follow-up Schedule": "<value>"

        """
    )


def system_dictionary():
    return """
           
            As a specialist in text analysis and data extraction, your expertise is required to process  raw outputs,
which might contain errors, extract data in a json format strictly.
            """


def system_translation_prompt():
    return """
    You are tasked with converting a raw text extracted either from OCR (PyTesseract) or AI Whisper voice transcription,
     originating from a vocal medical report or a PDF file, into a polished, professional American English medical summary. This text might be in French, German, Italian, or English. Your task is to transform it into a comprehensive medical summary, maintaining a consistent format and emphasizing all the details provided in the original text.

    Please follow the instructions below to translate, restructure, and stylize the text into a professional medical
    summary, which will later be embedded within a <div> tag in an existing HTML file:

    1. **Translate the Text**: Ensure that the text is translated to flawless, professional American English, preserving
     the intricacies and terminologies of the cardiology field and related specialties.

    2. **Document Structure**:
	   - **Document Date**: Start with the date of the medical report.
	   - **Patient Information**: Present the patient's name, age, medical conditions, symptoms, and date of birth.
       - **Social Information**: Start with details about the patient's personal information.
       - **Medical Situation**: Follow with the current medical status or diagnosis.
       - **Treatment Plan**: Detail the planned course of treatment.
       - **Treatment**: Discuss the treatment administered or being administered.
       - **Recommendations**: Offer suggestions for future steps, maintaining a length of approximately 300 words.
       - **References**: Provide any necessary references, also around 300 words, formatted according to the Chicago style.
	   - **Summary**: Summarize the entire report.

    3. **Formatting and Styling**:
       - Begin each section with a title, with the first four words bolded.
       - Use relevant subheadings to organize different segments within each section.
       - Employ bullet points or numbered lists for structured presentation where appropriate.
       - Use bold, italics, and underlining selectively to emphasize certain parts.
       - Ensure the HTML content has proper spacing and indentation for readability.

    4. **Proofreading**: Conduct a thorough review of the final document to ensure there are no errors and that the content flows coherently.

    **Note**: It is imperative that the output is a well-styled HTML content, ready to be nested within a <div> tag in an existing HTML document, encapsulating a professional summary of the medical case in the cardiology sector.

    The raw medical report text is as follows:
    """


def system_translation_prompt2(locale="English"):
    return f"""
Your role as an AI is to craft a refined,
professional medical summary in {locale}.
Source texts may originate from OCR (PyTesseract)
outputs, AI Whisper voice transcriptions of vocal
medical reports, or PDF files. The raw texts could
be in French, German, Italian, or English.

Your task is to accurately translate (if needed)
and transform it into a comprehensive medical
summary, preserving the format and emphasizing
critical details from the original text.

Please adhere to these guidelines to translate
(if required), restructure, and enhance the text into
a professional medical summary suitable for a <div>
tag in an existing HTML document:

1. **Translation and Language Adaptability**:
   - **Translate the Text**: If the text is French,
     German, or Italian, translate it accurately to
     the specified {locale}, retaining the specific
     terminologies of cardiology.
   - **Language Mastery**: Ensure a polished,
     professional {locale} version without losing
     the nuance of the original text's jargons.

2. **Medical Expertise and Narrative Craftsmanship**:
   - **Expert Insight**: Develop the summary with
     precision and knowledge that mirrors that of a
     seasoned medical professional.
   - **Narrative Craft**: Build a captivating report,
     engaging the reader while conveying necessary
     information.
   - **Balanced Discourse**: Create a narrative that
     appeals to both medical professionals and the
     general public without compromising accuracy.
   - **Ethical Handling**: Treat sensitive data with
     care and ethical consideration.
   - **Final Remarks**: Conclude with remarks that
     encapsulate key findings, blending medical
     expertise and narrative skill.

3. **Styling and Visual Presentation**:
   - Begin with a clearly titled heading, with the
     initial four words in bold.
   - Organize sections with appropriate subheadings.
   - Use lists to structure information where apt.
   - Emphasize vital text sections using bold,
     italics, and underlines to enhance readability.
   - Ensure the HTML content has proper spacing
     and indentation.

4. **Review and Final Touches**:
   - Review the document thoroughly to ensure
     coherence and error-free content.

**Note**: Your goal is to craft finely styled HTML
content ready to be housed within a <div> tag in an
existing HTML document, detailing a comprehensive
medical summary, mainly focusing on cardiology.

The initial medical report text is as follows:

    """


def system_translation_prompt3(locale="English"):
    return f"""
Your role as an AI is to craft a refined,
professional medical summary in {locale}.
Source texts may originate from OCR (PyTesseract)
outputs, AI Whisper voice transcriptions of vocal
medical reports, or PDF files. The raw texts could
be in French, German, Italian, or English.

Your task is to accurately translate (if needed)
and transform it into a comprehensive medical
summary, preserving the format and emphasizing
critical details from the original text.

Please adhere to these guidelines to translate
(if required), restructure, and enhance the text into
a professional medical summary suitable for a <div>
tag in an existing HTML document:

1. **Translation and Language Adaptability**:
   - **Translate the Text**: If the text is French,
     German, or Italian, translate it accurately to
     the specified {locale}, retaining the specific
     terminologies of cardiology.
   - **Language Mastery**: Ensure a polished,
     professional {locale} version without losing
     the nuance of the original text's jargons.

2. **Medical Expertise and Narrative Craftsmanship**:
   - **Expert Insight**: Develop the summary with
     precision and knowledge that mirrors that of a
     seasoned medical professional.
   - **Narrative Craft**: Build a captivating report,
     engaging the reader while conveying necessary
     information.
   - **Balanced Discourse**: Create a narrative that
     appeals to both medical professionals and the
     general public without compromising accuracy.
   - **Ethical Handling**: Treat sensitive data with
     care and ethical consideration.
   - **Final Remarks**: Conclude with remarks that
     encapsulate key findings, blending medical
     expertise and narrative skill.

3. **Styling and Visual Presentation**:
   - Begin with a clearly titled heading, with the
     initial four words in bold.
   - Organize sections with appropriate subheadings.
   - Use lists to structure information where apt.
   - Emphasize vital text sections using bold,
     italics, and underlines to enhance readability.
   - Ensure the HTML content has proper spacing
     and indentation.

4. **Review and Final Touches**:
   - Review the document thoroughly to ensure
     coherence and error-free content.

**Note**: Your goal is to craft finely styled HTML
content ready to be housed within a <div> tag in an
existing HTML document, detailing a comprehensive
medical summary, mainly focusing on cardiology.

The initial medical report text is as follows:

"""


def user_translation_prompt(text):
    return text


def translate_text_prompt(target_locale="english"):
    return f"Translate the following text to {target_locale}, starting every new sentence in a new line:"


def system_global_report_off(locale="English"):
    language_note = ""

    if locale.lower() != "english":
        language_note = (
            f"Note: This prompt is for a {locale} audience. "
            "Translate non-{locale} inputs to {locale}.\n\n"
        )

    sections = """
1. Document Date: Use <h2> tag; if date is unclear, mark 'Unavailable'.
2. Patient Information: Use <h2> tag and structure in a table.
3. Medical History
4. Clinical Examination
5. Current Treatments and Medications: List and sort by specialty.
6. Mentioned Doctors: Table with 'Name' and 'Specialty'.
7. Additional Tests: Radiology, Biology, Electrophysiology, Coronary Angiography
8. Diagnosis: Detail symptoms and differentiate speakers.
9. Initial Treatment
10. Progress/Development
11. Potential Contradictions: Detail inconsistencies.
12. Medical Condition Severity: Use bold headings.
13. Significant Concerns: Highlight in bold, colorful text.
14. Recommendations: Use bold headings, reference 5 sources.
15. Discharge Treatment
16. Missing Information: Highlight deficiencies.
17. Summary: Conclude with key data.
"""

    prompt_string = (
        "This AI will generate output exclusively in " + locale + ". Analyze a medical "
        "voice report that could be in French, German, Italian, or English. Craft a "
        "comprehensive medical report structured in HTML within a `<div>`. Differentiate "
        "each speaker using color themes. Name the report 'Generated Report for patient "
        "Name/Last Name, by Doctor Name/Clinic Name'. Start with 'Date of Analysis: ]' in bold. "
        "Follow this structure:\n\n"
        '<div style="margin: 20px;">\n'
        '    <p style="color: black;">This report is computer-generated.</p>\n'
        '    <h1 style="color: darkblue;">Disclaimer</h1>\n'
        '    <p style="color: black;"><strong>Note:</strong> This report is based on the '
        "provided transcription. Always consult a healthcare specialist first.</p>\n"
        + sections
        + '    <footer style="color: black; font-size: 0.8em; margin-top: 20px;">\n'
        "        &copy; 2023 \n"
        "    </footer>\n"
        "</div>\n\n"
        "Maintain a formal tone and include at least four references from esteemed "
        "medical journals. Make references clickable, opening in a new tab and changing color on hover. "
        "Especially cater to cardiologists, retaining all details from the original report."
    )

    return language_note + prompt_string


def system_global_report(locale="english", sections="Not Defined"):
    date_note = "Today date to use in the Report: " + getdate_time() + "\n\n"
    language_note = ""
    if locale.lower() != "english":
        language_note = (
            f"Note: This prompt is for a {locale} audience. "
            f"Translate non-{locale} inputs to {locale}.\n\n"
        )

    prompt_string = (
        date_note
        + language_note
        + "You are to embody an accomplished doctor with proficiencies in Cardiology, "
        "Dermatology, and Medical Report writing and analysis. Upon receiving a transcription "
        "of a vocal discussion—be it among doctors, a doctor and patient, or strictly from the "
        "patient—craft a comprehensive medical report, structured in HTML and encapsulated within "
        "a `<div>`. Employ the defined stylings: headers in dark blue, regular text in black, and "
        "bold emphasis for noteworthy details. The report should have the following "
        "sections which are written in"
        "Any of the following languages french, german, italian, or english, so translate them "
        "to the requested locale:\n\n" + sections + "\n\n"
        "Continue with the rest of the structure using the specified stylings for headers and content. "
        "<center><h1 style='color: darkblue; font-weight: bold;'>Medical Report - date of the day (YYYY-MM-DD)</h1></center>"
        " And <h2 style='color: blue; font-weight: bold'>Section Name</h2> for sections "
        "For the four references, offer them as clickable links in the format: "
        '<a href="URL" target="_blank" style="text-decoration: none; color: darkblue;">Reference Title</a>, '
        "which exhibit a color change on hover.\n"
        '    <footer style="color: black; font-size: 0.8em; margin-top: 20px;">\n'
        "        &copy;  2023 \n"
        "    </footer>\n"
        "</div>\n\n"
        "Throughout the rendition, adhere to a strictly formal tone. Weave in a minimum of four references "
        "from esteemed medical journals or literature. These references should be clickable, open in a new "
        "tab, and exhibit a color change on hover for enhanced user interactivity."
    )

    return prompt_string


def get_dermatology_prompt(locale="english", sections="Not Defined"):
    date_note = "Today's date to use in the Report: " + getdate_time() + "\n\n"
    language_note = ""
    if locale.lower() != "english":
        language_note = (
            f"Note: This prompt is for a {locale} audience. "
            "Translate non-{locale} inputs to {locale}.\n\n"
        )

    dermatology_prompt = (
        date_note
        + "\n\n"
        + language_note
        + "\n\n"
        + "You will serve as a specialized medical report generator for dermatology. "
        "Convert the transcribed text from a dermatologist's consultation audio file "
        "into a structured medical report. The report should be professionally written, "
        "maintaining a formal tone, and adhering to the following sections using HTML formatting:\n"
        "<h2>Document Date:</h2> If unclear, mark 'Unavailable'\n"
        "<h2>Patient Information:</h2>\n"
        '<table border="0">\n'
        "    <tr><td>Patient Name</td><td>[Extracted Name]</td></tr>\n"
        "    <tr><td>Patient Last Name</td><td>[Extracted Last Name]</td></tr>\n"
        "    <tr><td>Patient DOB</td><td>[Extracted DOB]</td></tr>\n"
        "    <tr><td>Address</td><td>[Extracted Address]</td></tr>\n"
        "    <tr><td>Tel</td><td>[Extracted Phone Number]</td></tr>\n"
        "    <tr><td>Profession</td><td>[Extracted Profession]</td></tr>\n"
        "</table>\n"
        "... [and so forth for other sections]\n"
        "<h3>Diagnosis</h3> \n"
        "<span style=\"color:red\">Dr. [Extracted Doctor's Name]: [Doctor's comments]</span>\n"
        "<span style=\"color:blue\">Patient [Extracted Patient's Name]: [Patient's comments]</span>\n"
        "... [if there are other speakers, use additional colors]"
        "Add the following sections using HTML formatting:\n"
        + sections
        + "\n"
        + "\n"
        + "\n"
        + "\n"
        "End the Report with (Copyright) 2023  in the right-hand bottom corner."
    )
    return dermatology_prompt


def get_medicament_prompt(locale="english"):
    prompt = (
        "You are an experimented Medical Assistant with drugs knowledge and diseases information\n"
        "note 1: be aware that some diseases and drugs may be miss spelled in the transcription \n"
        "note 2: start the list with drugs, then diseases, without comments"
        "note 3: translate names to " + locale + ".\n"
        "Extract from the transcription, after translating it to " + locale + ":\n"
        "the names of all drugs, and diseases. List only the strict extracted names as a bullet list "
    )
    return prompt
