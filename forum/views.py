from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator # For paginating threads and posts
from .models import ForumCategory, ForumThread, ForumPost
from .forms import ThreadCreateForm, PostCreateForm
from django.utils import timezone # For the ForumPost save method if needed

def forum_home_view(request):
    categories = ForumCategory.objects.all()
    # Optionally, fetch recent threads or stats for display on home
    context = {
        'categories': categories,
        'page_title': "Discussion Forums"
    }
    return render(request, 'forum/forum_home.html', context)

def category_detail_view(request, category_slug):
    category = get_object_or_404(ForumCategory, slug=category_slug)
    threads_list = category.threads.all().order_by('-updated_at') # Already default order

    paginator = Paginator(threads_list, 10) # Show 10 threads per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'category': category,
        'page_obj': page_obj, # Pass paginated threads
        'page_title': category.name
    }
    return render(request, 'forum/category_detail.html', context)

@login_required
def thread_detail_view(request, category_slug, thread_slug):
    thread = get_object_or_404(
        ForumThread.objects.select_related('author', 'category'),
        category__slug=category_slug, slug=thread_slug
    )
    posts_list = thread.posts.all().select_related('author', 'author__profile').order_by('created_at')

    paginator = Paginator(posts_list, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.method == 'POST':
        post_form = PostCreateForm(request.POST)
        if post_form.is_valid():
            new_post = post_form.save(commit=False)
            new_post.thread = thread
            new_post.author = request.user
            new_post.save()  # This updates thread.updated_at
            
            messages.success(request, "Your reply has been posted.")
            
            # Award points for posting
            points_for_post = 5
            request.user.profile.award_points(
                points_for_post,
                reason=f"Posted in thread: {thread.title[:30]}..."
            )
            messages.info(request, f"You earned {points_for_post} points for your contribution!")
            # check_and_award_badges(request.user)  # Uncomment if badge logic exists
            
            return redirect(thread.get_absolute_url() + f"?page={paginator.num_pages}")
    else:
        post_form = PostCreateForm()

    context = {
        'thread': thread,
        'category': thread.category,
        'page_obj': page_obj,
        'post_form': post_form,
        'page_title': thread.title,
    }
    return render(request, 'forum/thread_detail.html', context)

@login_required
def create_thread_view(request, category_slug):
    category = get_object_or_404(ForumCategory, slug=category_slug)
    if request.method == 'POST':
        thread_form = ThreadCreateForm(request.POST)
        # For combined thread + first post form:
        # initial_post_form = PostCreateForm(request.POST, prefix="post") # Use prefix if two forms
        if thread_form.is_valid(): # and initial_post_form.is_valid():
            new_thread = thread_form.save(commit=False)
            new_thread.category = category
            new_thread.author = request.user
            new_thread.save() # Save thread first to get an ID

            # Create the first post (if handling initial post content with thread form)
            # first_post_content = thread_form.cleaned_data.get('initial_post_content')
            # if first_post_content:
            #     ForumPost.objects.create(
            #         thread=new_thread,
            #         author=request.user,
            #         content=first_post_content
            #     )
            # else:
            # Assume the first post content comes from a separate field in the combined form
            # initial_post = initial_post_form.save(commit=False)
            # initial_post.thread = new_thread
            # initial_post.author = request.user
            # initial_post.save()

            messages.success(request, "New thread created successfully! Add your first post.")
            return redirect(new_thread.get_absolute_url()) # Redirect to the new thread page
    else:
        thread_form = ThreadCreateForm()
        # initial_post_form = PostCreateForm(prefix="post")

    context = {
        'category': category,
        'thread_form': thread_form,
        # 'initial_post_form': initial_post_form,
        'page_title': f"New Thread in {category.name}"
    }
    return render(request, 'forum/create_thread.html', context)