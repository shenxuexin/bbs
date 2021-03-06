from django.conf.urls import url
from my_bbs import views

urlpatterns = [
    url(r'^register$', views.RegisterView.as_view(), name='register'),
    url(r'^login$', views.LoginView.as_view(), name='login'),
    url(r'^logout$', views.LogoutView.as_view(), name='logout'),
    url(r'^user/active/(?P<token>.+)$', views.AcitveView.as_view(), name='active'),
    url(r'^detail/(?P<article_id>\d+)$', views.DetailView.as_view(), name='detail'),
    url(r'^center/article$', views.CenterArticleView.as_view(), name='article_manage'),
    url(r'^center/comment$', views.CenterCommentView.as_view(), name='comment_manage'),
    url(r'^center/sort$', views.CenterSortView.as_view(), name='sort_manage'),
    url(r'^center/tag$', views.CenterTagView.as_view(), name='tag_manage'),
    url(r'^center/promotion$', views.CenterPromotion.as_view(), name='promotion_manage'),
    url(r'^new_article$', views.CreateArticleView.as_view(), name='create_article'),
    url(r'^edit_article/(?P<aid>\d+)$', views.EditArticleView.as_view(), name='edit_article'),
    url(r'^list/tag/(?P<tag_id>\d+)$', views.TagListView.as_view(), name='tag_list'),
    url(r'^list/sort/(?P<sort_id>\d+)$', views.SortListView.as_view(), name='sort_list'),
    url(r'^list/date/(?P<date>.+)$', views.DateListView.as_view(), name='date_list'),
    url(r'^comment$', views.CommentView.as_view(), name='comment'),
    url(r'^del_article$', views.DelArticleView.as_view(), name='del_article'),
    url(r'^del_comment$', views.DelCommentView.as_view(), name='del_comment'),
    url(r'^top_comment$', views.TopCommentView.as_view(), name='top_comment'),
    url(r'^down_comment$', views.DownCommentView.as_view(), name='down_comment'),
    url(r'^del_sort$', views.DelSortView.as_view(), name='del_sort'),
    url(r'^del_tag$', views.DelTagView.as_view(), name='del_tag'),
    url(r'^create_sort$', views.CreateSortView.as_view(), name='create_sort'),
    url(r'^edit_sort$', views.EditSortView.as_view(), name='edit_sort'),
    url(r'^create_tag$', views.CreateTagView.as_view(), name='create_tag'),
    url(r'^edit_tag$', views.EditTagView.as_view(), name='edit_tag'),
    url(r'^del_promotion$', views.DelPromotionView.as_view(), name='del_promotion'),
    url(r'^create_promotion$', views.CreatePromotionView.as_view(), name='create_promotion'),
    url(r'^edit_promotion$', views.EditPromotionView.as_view(), name='edit_promotion'),
    url(r'^article_up$', views.ArticleUpView.as_view(), name='article_up'),
    url(r'^file/upload$', views.FileUploadView.as_view(), name='upload'),
    url(r'^$', views.IndexView.as_view(), name='index'),

]
