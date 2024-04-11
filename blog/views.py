from re import search
from django.core.mail import send_mail
from django.http import Http404
from django.shortcuts import render, get_object_or_404

from .forms import EmailPostForm, CommentForm, SearchForm
from .models import Post, Comment
from django.core.paginator import EmptyPage, Paginator, PageNotAnInteger
from django.views.generic import ListView
from django.views.decorators.http import require_POST
from taggit.models import Tag
from django.db.models import Count
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.contrib.postgres.search import TrigramSimilarity
# Create your views here.


class PostListView(ListView):
    queryset = Post.published.all()
    context_object_name = 'posts'
    paginate_by = 3
    template_name = 'blog/post/list.html'


def post_list(request, tag_slug=None):
    post_list = Post.published.all()
    
    tag = None
    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        post_list = post_list.filter(tags__in=[tag])
    # количество постов на странице 3
    paginator = Paginator(post_list, 3)
    # берет номер страницы, если нет то берет страницу 1
    page_number = request.GET.get('page', 1)
    try:
        posts = paginator.page(page_number)
    except PageNotAnInteger:
        # елси page_number не int то выдает страницу 1
        posts = paginator.page(1)
    except EmptyPage:
        #последняя страница
        posts = paginator.page(paginator.num_pages)
    return render(request,
                'blog/post/list.html',
                {'posts': posts, 'tag': tag},)


def post_detail(request, year, month, day, post):
    post = get_object_or_404(Post,
                            status=Post.Status.PUBLISHED,
                            slug=post,
                            publish__year=year,
                            publish__month=month,
                            publish__day=day,)
    # список комментариев 
    comments = post.comments.filter(active=True)
    # форма для комментариев 
    form = CommentForm()
    
    # список похожих постов
    post_tags_ids = post.tags.values_list('id', flat=True)
    similar_posts = Post.published.filter(tags__in=post_tags_ids).exclude(id=post.id)
    similar_posts = similar_posts.annotate(same_tags=Count('tags')).order_by('-same_tags', '-publish')[:4]
    
    return render(request,
                    'blog/post/detail.html',
                    {'post': post, 'comments': comments, 'form': form, 'similar_posts': similar_posts})


@require_POST
def post_comment(request, post_id):
    post = get_object_or_404(Post,
                            id=post_id,
                            status=Post.Status.PUBLISHED)
    comment = None
    # комметарий отправлен
    form = CommentForm(data=request.POST)
    if form.is_valid():
        # создаем обьект класса Comment, не сохраняя его в БД
        comment = form.save(commit=False)
        # назначение поста для комментария
        comment.post = post
        # сохранение комментария
        comment.save()
    return render(request,
                'blog/post/comment.html',
                {'post': post, 'fomr': form, 'comment': comment})



def post_share(request, post_id):
    post = get_object_or_404(Post,
                            id=post_id,
                            status=Post.Status.PUBLISHED)
    sent = False
    
    if request.method == 'POST':
        form = EmailPostForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            post_url = request.build_absolute_uri(post.get_absolute_url())
            subject = f"{cd['name']} рекомендовал вам пост {post.title}"
            message = f"Прочтите пост {post.title} по ссылке {post_url}\n\n"
            # отправка email
            send_mail(subject, message, 'django.test@internet.ru', [cd['to']])
            sent = True
    else:
        form = EmailPostForm()
    return render(request,
                'blog/post/share.html',
                {'post': post, 'form': form, 'sent': sent})



def post_search(request):
    # поиск
    form = SearchForm()
    # поисковой запрос
    query = None
    results = []
    
    if 'query' in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data['query']
            
            # results = Post.published.annotate(
            #     similarity=TrigramSimilarity('title', query),
            # ).filter(similarity__gt=0.1).order_by('-similarity')  
            
            search_vector = SearchVector('title', weight='A', config='russian') + SearchVector('body', weight='B', config='russian') # поля в которых будет производится поиск
            search_query = SearchQuery(query, config='russian') # поискововй запрос
            #результат поиска. создаются дополнительные поля search и rank
            results = Post.published.annotate(search=search_vector,
                                            rank=SearchRank(search_vector, search_query)
                                            ).filter(ranl__gre=0.3).order_by('-rank')
    
    return render(request,
                'blog/post/search.html',
                {'form': form, 'query': query, 'results': results})

