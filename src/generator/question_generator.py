import os
import json
from typing import List, Dict, Any
from dotenv import load_dotenv
from groq import Groq

class MockChromaDB:
    def get_relevant_chunks(self, lesson_id: str) -> List[Dict[str, Any]]:
        print(f"Fetching mock slide chunks for lesson_id: {lesson_id}")
        return [
            {"slide_id": 1, "text": "Introduction to Python programming.", "metadata": {"lesson_id": lesson_id}},
            {"slide_id": 2, "text": "Discussing variables, data types, and basic syntax.", "metadata": {"lesson_id": lesson_id}},
            {"slide_id": 3, "text": "Exploring control flow with if-else statements and loops.", "metadata": {"lesson_id": lesson_id}},
        ]

class QuestionGenerator:
    def __init__(self):
        self.client = Groq()
        self.model = "llama-3.3-70b-versatile"

    def _get_prompt_text(self, lesson_title: str, slide_context: str) -> str:
        template = f"""
        Based on the following lesson context from a slide deck, please generate a set of questions.
        The lesson title is "{lesson_title}".

        Context from slides:
        {slide_context}

        Generation Rules:
        1. Generate a mix of question types: Multiple Choice (MCQ) and True/False.
        2. Ensure questions are directly based on the provided context.
        3. Output MUST be a valid JSON array of objects.
        4. Each object should have the following keys: "question_type", "question_text", "options" (for MCQ), "answer", and "slide_id" (the slide number the question is based on).
        5. For True/False questions, "options" should be ["True", "False"].
        6. For Short Answer questions, "options" should be an empty list.

        Example JSON output:
        [
            {{
                "question_type": "MCQ",
                "question_text": "What is a variable in Python?",
                "options": ["A type of data", "A reserved keyword", "A container for storing data values", "A function"],
                "answer": "A container for storing data values",
                "slide_id": 2
            }},
            {{
                "question_type": "True/False",
                "question_text": "Python uses curly braces for defining blocks of code.",
                "options": ["True", "False"],
                "answer": "False",
                "slide_id": 3
            }}
        ]

        Now, generate the questions based on the provided context.
        """
        return template

    def _format_context(self, slide_chunks: List[Dict[str, Any]]) -> str:
        formatted_context = ""
        for chunk in slide_chunks:
            formatted_context += f"[slide_id: {chunk['slide_id']}] {chunk['text']}\n"
        return formatted_context.strip()

    def _validate_and_clean_json(self, raw_output: str) -> List[Dict[str, Any]]:
        try:
            first_fence_idx = raw_output.find("```")
            last_fence_idx = raw_output.rfind("```")

            json_content = ""
            if first_fence_idx != -1 and last_fence_idx != -1 and first_fence_idx != last_fence_idx:
                json_content = raw_output[first_fence_idx + 3 : last_fence_idx].strip()
                if json_content.lower().startswith("json"):
                    json_content = json_content[4:].strip()
            else:
                json_content = raw_output.strip()

            questions = json.loads(json_content)

            if not isinstance(questions, list):
                raise ValueError("JSON output is not a list.")

            for q in questions:
                if not all(k in q for k in ["question_type", "question_text", "answer", "slide_id"]):
                    raise ValueError("Missing required keys in a question object.")

            return questions
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            return []
        except ValueError as e:
            print(f"Error in JSON structure: {e}")
            return []

    def generate_questions_for_lesson(self, lesson_id: str, lesson_title: str) -> List[Dict[str, Any]]:
        mock_db = MockChromaDB()
        slide_chunks = mock_db.get_relevant_chunks(lesson_id)
        if not slide_chunks:
            print(f"No content found for lesson_id: {lesson_id}")
            return []

        slide_context = self._format_context(slide_chunks)
        
        prompt_text = self._get_prompt_text(lesson_title, slide_context)

        print(f"Generating questions with the Groq model: {self.model}...")
        
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt_text,
                }
            ],
            temperature=0.3,
        )
        
        raw_output = completion.choices[0].message.content

        print("\n--- Raw LLM Output ---")
        print(raw_output)
        print("----------------------\n")

        print("Validating and cleaning LLM output...")
        validated_questions = self._validate_and_clean_json(raw_output)

        return validated_questions

if __name__ == '__main__':
    load_dotenv()
    if not os.getenv("GROQ_API_KEY"):
        print("Please set the GROQ_API_KEY environment variable to run this example.")
    else:
        question_generator = QuestionGenerator()

        test_lesson_id = "python-101"
        test_lesson_title = "Introduction to Python"

        generated_questions = question_generator.generate_questions_for_lesson(
            lesson_id=test_lesson_id,
            lesson_title=test_lesson_title
        )

        if generated_questions:
            print("\n--- Generated Questions ---")
            print(json.dumps(generated_questions, indent=2))
            print("\nSuccessfully generated and validated questions.")
        else:
            print("\nFailed to generate questions.")
