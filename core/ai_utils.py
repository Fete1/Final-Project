# ai_elearning_platform/core/ai_utils.py
import openai
from django.conf import settings

def get_openai_client():
    """Initializes and returns the OpenAI API client."""
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not configured in settings.")
    
    
    client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    return client

def get_chat_response(prompt_message, model="gpt-4o-mini"):
    """
    Gets a chat response from OpenAI.
    prompt_message should be a string for a simple user query.
    """
    client = get_openai_client()
    try:
        
        # The 'messages' parameter expects a list of message objects.
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant for an e-learning platform."},
                {"role": "user", "content": prompt_message}
            ]
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"OpenAI API Error: {e}")
        return "Sorry, I couldn't process your request at the moment."

def get_saq_feedback(question_text, user_answer_text, ideal_answer_keywords=None, model="gpt-4o-mini"): 
    client = get_openai_client() 
    prompt = f"""
    You are an expert AI grading assistant for an e-learning platform, providing detailed, constructive feedback to students on their short answer questions.
    
    Your Task:
    1. Analyze the student's answer for correctness, completeness, and clarity based on the question.
    2. Provide a summary of your analysis, highlighting strengths and areas for improvement, avoiding revealing the 'ideal answer' directly. 
    3. Assign a score from 0 to 10 based on a detailed rubric. 
       - 10: Excellent - comprehensive, accurate, insightful, and well-expressed.
       - 8-9: Very Good - mostly correct, addresses key points, well-organized.
       - 6-7: Good - generally correct, may lack some details or clarity.
       - 4-5: Fair - partially correct, misses key aspects, some confusion or inaccuracies.
       - 2-3: Poor - significantly incomplete or inaccurate, demonstrates limited understanding.
       - 0-1: Very Poor/Irrelevant - fails to address the question or is completely incorrect.
    4. Present the feedback clearly, with the score and rubric. For example:
       "Feedback: Your answer shows a good understanding of the core concept. However, you could expand on [specific point] to make it more comprehensive.
        Preliminary Score: 7/10 (Good - generally correct, may lack some details or clarity.)"

    The Short Answer Question: "{question_text}"
    Student's Answer: "{user_answer_text}"
    """
    if ideal_answer_keywords:
        prompt += f"""\nConsider these keywords/concepts as crucial for an ideal answer: {', '.join(ideal_answer_keywords)}"""
    prompt += "\n\nFeedback and Preliminary Score:"
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an AI grading assistant providing feedback and a preliminary score for student short answer questions."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=250,
            temperature=0.4,
        )
        
        if response.choices and response.choices[0].message and response.choices[0].message.content:
            feedback_content = response.choices[0].message.content.strip()
            return feedback_content
        else:
            return "AI response was empty or malformed."

    except openai.APIError as e: 
        return f"Error communicating with AI (APIError): {str(e)}. Please try again later."
    except Exception as e:
        return f"Could not generate feedback due to an unexpected error: {str(e)}."

    except Exception as e:
        print(f"OpenAI SAQ Feedback Error: {e}")
        return f"Could not generate feedback or score at this time. Error: {e}"




