from django.http import Http404
from django.shortcuts import render, get_object_or_404
from .models import Post
from django.core.paginator import EmptyPage, Paginator, PageNotAnInteger
# Create your views here.

def post_list(request):
    post_list = Post.published.all()
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
                {'posts': posts},)


def post_detail(request, year, month, day, post):
    post = get_object_or_404(Post,
                            status=Post.Status.PUBLISHED,
                            slug=post,
                            publish__year=year,
                            publish__month=month,
                            publish__day=day,)
    return render(request,
                    'blog/post/detail.html',
                    {'post': post})

