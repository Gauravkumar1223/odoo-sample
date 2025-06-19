import os
import logging
import pypandoc

from azur_llm_pool import AzurePoolLLM  # Import the AzurePoolLLM class

logging.basicConfig(level=logging.INFO)


class CourseCreator:
    def __init__(self):
        self.course_topic = None
        self.azure_llm = AzurePoolLLM(stream=False)
        self.system_prompt = """You are a course creator, specialized in training experienced developers. You generate detailed content 
        for courses based on a given topic, writing in clear and easy-to-understand Markdown."""
        self.course_structure = {}

    def get_user_input(self):
        logging.info("Requesting user input for course topic.")
        return input("Enter the course topic you'd like to generate: ")

    def get_course_structure(self, topic):
        logging.info(f"Requesting course structure for topic: {topic}")
        user_prompt = f"Create a detailed course structure for {topic}, including main topics and subtopics."
        messages = [{"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}]
        structure = self.azure_llm.call_llm(messages)
        self.parse_course_structure(structure)
    def parse_course_structure(self, structure):
        # Implement logic to parse the structure into a nested dictionary of topics and subtopics
        lines = structure.split('\n')
        topic_tree = {}
        parents = []
        for line in lines:
            if line.startswith('## '):  # Main topic
                current_topic = line[3:].strip()
                topic_tree[current_topic] = []
                parents = [topic_tree, current_topic]
            elif line.startswith('* '):  # Subtopic
                if len(parents) > 0:
                    parent_topic = parents[-1]
                    parent_dict = parents[-2]
                    subtopic = line[2:].strip()
                    parent_dict[parent_topic].append(subtopic)

        self.course_structure = topic_tree

    def develop_content(self, topic, is_subtopic=False):
        logging.info(f"Developing content for {'subtopic' if is_subtopic else 'topic'}: {topic}")
        # A specific, context-rich prompt to elicit detailed and relevant exposition on the topic
        prefix = "subtopic" if is_subtopic else "chapter"
        user_prompt = f"Please provide a comprehensive educational write-up on the {prefix} titled '{topic}'. " \
                      "Include key concepts, important context, and any relevant examples or case studies. " \
                      "Your content should be well-researched, informative, and presented in a way that is accessible to students " \
                      "with a basic understanding of the subject matter. Use Markdown formatting for structure and emphasis where appropriate."
        messages = [{"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}]
        return self.azure_llm.call_llm(messages)

    def format_in_markdown(self):
        logging.info("Formatting course content in Markdown.")
        markdown_content = f"# Course on {self.course_topic}\n\n"
        for chapter_num, (topic, subtopics) in enumerate(self.course_structure.items(), 1):
            markdown_content += f"## Chapter {chapter_num}: {topic}\n\n"
            markdown_content += self.develop_content(topic) + "\n\n"
            for section_num, subtopic in enumerate(subtopics, 1):
                markdown_content += f"### Section {chapter_num}.{section_num}: {subtopic}\n\n"
                markdown_content += self.develop_content(subtopic, is_subtopic=True) + "\n\n"
        return markdown_content

    def save_to_file(self, content, base_filename):
        markdown_filename = f"{base_filename}.md"
        docx_filename = f"{base_filename}.docx"
        pdf_filename = f"{base_filename}.pdf"

        logging.info(f"Saving course content to Markdown file: {markdown_filename}")
        with open(markdown_filename, "w") as file:
            file.write(content)

        try:
            logging.info(f"Converting Markdown to DOCX: {docx_filename}")
            pypandoc.convert_text(content, 'docx', format='md', outputfile=docx_filename)
        except:
            logging.warning("Failed to convert Markdown to DOCX.")


    def create_course(self):
        self.course_topic = self.get_user_input()
        self.get_course_structure(self.course_topic)
        markdown_content = self.format_in_markdown()
        filename = self.course_topic.replace(" ", "_") + "_Course.md"
        self.save_to_file(markdown_content, filename)
        logging.info("Course creation completed.")

def main():
    logging.info("Starting Course Creator.")
    course_creator = CourseCreator()
    course_creator.create_course()

if __name__ == "__main__":
    main()