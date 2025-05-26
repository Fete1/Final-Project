from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required
from users.models import Profile 
from django.shortcuts import render 
from django.http import JsonResponse 
from .ai_utils import get_chat_response 
import json 
from django.shortcuts import render, redirect 
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .ai_utils import get_chat_response
import json
from django.shortcuts import render
from courses.models import Course, UserLessonProgress
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from django.db.models import Q
import json
import time 
from django.http import StreamingHttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt 
from django.views.decorators.http import require_POST
from django.conf import settings
import openai 
from .ai_utils import get_openai_client
CONVERSATION_SESSIONS = {} 

def generate_ai_response_chunks(user_message, session_id=None):
    """
    Generator function to get response from OpenAI (or other LLM) and yield it in chunks.
    Each chunk should be a JSON string followed by a newline.
    """
    client = get_openai_client()
    if session_id and session_id in CONVERSATION_SESSIONS:
        history = CONVERSATION_SESSIONS[session_id]
    else:
        session_id = f"chat_session_{int(time.time())}" # Generate a new session ID
        history = [{"role": "system", "content": "You are a helpful AI Tutor for an e-learning platform. Provide concise and helpful answers. You can use Markdown for formatting."}]
    
    history.append({"role": "user", "content": user_message})
    CONVERSATION_SESSIONS[session_id] = history # Update session history

    try:
        # Using OpenAI's streaming API
        stream = client.chat.completions.create(
            model=getattr(settings, 'OPENAI_CHAT_MODEL', "gpt-4o-mini"), 
            messages=history,
            stream=True,
            max_tokens=150, 
            temperature=0.7, 
        )

        accumulated_bot_response = ""
        for chunk in stream:
            if chunk.choices[0].delta and chunk.choices[0].delta.content:
                content_chunk = chunk.choices[0].delta.content
                accumulated_bot_response += content_chunk
                # Yield each piece of content as a JSON object string + newline
                yield json.dumps({"message": content_chunk, "session_id": session_id}) + '\n'
                # time.sleep(0.01) # Optional small delay for more "natural" typing feel if chunks are too fast
        
        # Update history with the full bot response
        if accumulated_bot_response:
            history.append({"role": "assistant", "content": accumulated_bot_response})
            CONVERSATION_SESSIONS[session_id] = history
        
        # Send a final marker indicating the stream is done, along with the session_id
        yield json.dumps({"message": "[DONE]", "session_id": session_id}) + '\n'

    except openai.APIError as e:
        error_message = f"OpenAI API Error: {str(e)}"
        print(error_message)
        yield json.dumps({"error": "Sorry, I encountered an issue with the AI service.", "details": str(e)}) + '\n'
        yield json.dumps({"message": "[DONE]", "session_id": session_id}) + '\n' # Still send DONE
    except Exception as e:
        error_message = f"An unexpected error occurred: {str(e)}"
        print(error_message)
        yield json.dumps({"error": "An unexpected error occurred. Please try again.", "details": str(e)}) + '\n'
        yield json.dumps({"message": "[DONE]", "session_id": session_id}) + '\n'


@csrf_exempt 
@require_POST
def chatbot_api_stream_view(request): 
    try:
        data = json.loads(request.body.decode('utf-8'))
        user_message = data.get('message')
        session_id = data.get('session_id')

        if not user_message:
            return JsonResponse({"error": "Message cannot be empty."}, status=400)

        # Create the streaming HTTP response
        response_stream = generate_ai_response_chunks(user_message, session_id)
        return StreamingHttpResponse(response_stream, content_type='application/x-ndjson')

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON payload."}, status=400)
    except Exception as e:
        return JsonResponse({"error": "An internal server error occurred."}, status=500)
    
TFIDF_VECTORIZER = None
TFIDF_MATRIX = None
TFIDF_COURSE_IDS = [] # To map matrix rows back to course IDs

def get_tfidf_data():
    global TFIDF_VECTORIZER, TFIDF_MATRIX, TFIDF_COURSE_IDS
    # In a real app, you'd add cache invalidation logic if courses are updated
    # For simplicity, we recompute if it's None (e.g., on server restart)
    if TFIDF_VECTORIZER is None or TFIDF_MATRIX is None:
        all_courses = list(Course.objects.all()) # Get all courses
        if not all_courses:
            TFIDF_VECTORIZER, TFIDF_MATRIX, TFIDF_COURSE_IDS = None, None, []
            return TFIDF_VECTORIZER, TFIDF_MATRIX, TFIDF_COURSE_IDS

        TFIDF_COURSE_IDS = [course.id for course in all_courses]
        
        # Create a corpus of course content
        corpus = [course.get_content_for_embedding() for course in all_courses] # Reusing this method

        TFIDF_VECTORIZER = TfidfVectorizer(stop_words='english', max_df=0.85, min_df=2, ngram_range=(1,2))
        # stop_words='english': removes common English words
        # max_df=0.85: ignore terms that appear in more than 85% of documents
        # min_df=2: ignore terms that appear in less than 2 documents
        # ngram_range=(1,2): consider both single words and two-word phrases

        TFIDF_MATRIX = TFIDF_VECTORIZER.fit_transform(corpus)
        
        
    return TFIDF_VECTORIZER, TFIDF_MATRIX, TFIDF_COURSE_IDS

CONVERSATION_SESSIONS = {}
def home_view(request):
    if request.user.is_authenticated:
        # For logged-in users, redirect them to their dashboard.
        # The dashboard already has recommendations and personalized info.
        return redirect('users:student_dashboard')
    else:
        # For anonymous users, show the landing page content.
        # Fetch generic "popular" courses for the landing page.
        # The TF-IDF/Embedding logic for personalized recommendations will now live in the dashboard view.
        
        # Generic recommendations for landing page (e.g., newest or manually featured)
        # We can keep the TF-IDF parts here simpler for unauthenticated users or just show newest
        
        # Simplest: Newest courses for landing page
        landing_page_courses = Course.objects.all().order_by('-created_at')[:3]
        

        context = {
            'recommended_courses': landing_page_courses, # For the "Popular Courses" section on landing page
            'is_landing_page': True # Flag to control elements in base.html if needed
        }
        return render(request, 'core/home.html', context)

def generate_ai_response_chunks(user_message, session_id=None, request=None): # Pass request for Django sessions
    """
    Generator function to get response from OpenAI and yield it in chunks
    for the streaming chatbot.
    """
    client = get_openai_client() # Uses your existing robust client setup

    # --- Manage Conversation History (Using Django Sessions - Recommended) ---
    if request is None:
        # Fallback if request is not passed (e.g., for testing, but not ideal for production)
        # This fallback means history won't persist correctly without the request object.
        print("WARNING: Request object not passed to generate_ai_response_chunks. Using in-memory session.")
        if session_id and session_id in CONVERSATION_SESSIONS:
            history = CONVERSATION_SESSIONS[session_id]
        else:
            session_id = session_id or f"chat_session_fallback_{int(time.time())}"
            history = [{"role": "system", "content": "You are a helpful AI Tutor for an e-learning platform. Provide concise and helpful answers. You can use Markdown for formatting."}]
        CONVERSATION_SESSIONS[session_id] = history # For fallback
    else:
        # Preferred method: Using Django sessions
        session_key_prefix = "chatbot_history_"
        if not session_id: # If no session_id from client, try to get from Django session or create new
            session_id = request.session.get('chatbot_active_session_id', f"chat_session_django_{int(time.time())}")
            request.session['chatbot_active_session_id'] = session_id
        
        session_history_key = f"{session_key_prefix}{session_id}"
        history = request.session.get(session_history_key, [
            {"role": "system", "content": "You are a helpful AI Tutor for an e-learning platform. Provide concise and helpful answers. Use Markdown for formatting."}
        ])

    # Append current user message to history
    history.append({"role": "user", "content": user_message})

    # Trim history to prevent exceeding token limits (simple example: keep last N messages)
    # A more sophisticated approach would count tokens.
    MAX_HISTORY_LENGTH = getattr(settings, 'CHATBOT_MAX_HISTORY_LENGTH', 10) # e.g., keep last 10 messages (system + user + assistant)
    if len(history) > MAX_HISTORY_LENGTH:
        # Keep the system prompt and the most recent N-1 messages
        history = [history[0]] + history[-(MAX_HISTORY_LENGTH-1):]

    try:
        stream = client.chat.completions.create(
            model=getattr(settings, 'OPENAI_CHAT_MODEL', "gpt-4o-mini"), # Use your preferred model
            messages=history,
            stream=True,
            temperature=getattr(settings, 'OPENAI_CHAT_TEMPERATURE', 0.7),
        )

        accumulated_bot_response_for_history = ""
        for chunk in stream:
            if chunk.choices[0].delta and chunk.choices[0].delta.content:
                content_chunk = chunk.choices[0].delta.content
                accumulated_bot_response_for_history += content_chunk
                yield json.dumps({"message": content_chunk, "session_id": session_id}) + '\n'
        
        # Append full assistant response to history
        if accumulated_bot_response_for_history:
            history.append({"role": "assistant", "content": accumulated_bot_response_for_history})
        
        # Save updated history to Django session (or fallback)
        if request:
            request.session[session_history_key] = history
            request.session.modified = True # Ensure session is saved
        else: # Fallback
            CONVERSATION_SESSIONS[session_id] = history

        # Send a final marker
        yield json.dumps({"message": "[DONE]", "session_id": session_id}) + '\n'

    except openai.APIError as e:
        error_message = f"OpenAI API Error: {str(e)}"
        print(error_message) # Log this properly
        yield json.dumps({"error": "Sorry, an issue occurred with the AI service.", "details": str(e), "session_id": session_id}) + '\n'
        yield json.dumps({"message": "[DONE]", "session_id": session_id}) + '\n'
    except Exception as e:
        error_message = f"An unexpected error occurred in stream: {str(e)}"
        print(error_message) # Log this properly
        yield json.dumps({"error": "An unexpected server error occurred. Please try again.", "details": str(e), "session_id": session_id}) + '\n'
        yield json.dumps({"message": "[DONE]", "session_id": session_id}) + '\n'

# --- API View for Streaming Chatbot ---
@csrf_exempt # Review CSRF implications for your setup
@require_POST
def chatbot_api_stream_view(request): # This is the view your JS should call
    try:
        data = json.loads(request.body.decode('utf-8'))
        user_message = data.get('message')
        session_id = data.get('session_id') # Client can send its current session_id

        if not user_message:
            return JsonResponse({"error": "Message cannot be empty."}, status=400)

        # Pass the request object to the generator for session handling
        response_stream = generate_ai_response_chunks(user_message, session_id, request=request)
        
        return StreamingHttpResponse(response_stream, content_type='application/x-ndjson')

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON payload."}, status=400)
    except Exception as e:
        print(f"Chatbot API Stream View Error: {e}") # Log the full error
        return JsonResponse({"error": "An internal server error occurred in API view."}, status=500)
def leaderboard_view(request):
    # Get top N users by points. Ensure profile_picture is selected to avoid N+1 queries in template.
    top_users_profiles = Profile.objects.select_related('user')\
                                        .filter(points__gt=0) \
                                        .order_by('-points')[:10] # Top 10 users with points > 0

    # Get current user's rank if they have points (can be a bit more complex for large datasets)
    current_user_rank = None
    if request.user.is_authenticated and request.user.profile.points > 0:
        # This is a simple rank calculation, might be slow on very large user bases
        # For large scale, dedicated ranking solutions or denormalization might be needed.
        higher_ranked_users_count = Profile.objects.filter(points__gt=request.user.profile.points).count()
        current_user_rank = higher_ranked_users_count + 1
    
    context = {
        'top_users_profiles': top_users_profiles,
        'current_user_rank': current_user_rank,
        'page_title': 'Leaderboard'
    }
    return render(request, 'core/leaderboard.html', context)