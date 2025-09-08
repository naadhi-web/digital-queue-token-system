from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("register/", views.register, name="register"),
    path("book/", views.book_token, name="book_token"),
    path("cancel/<int:token_id>/", views.cancel_token, name="cancel_token"),
    path("my/history/", views.my_history, name="my_history"),

    path("slots/", views.list_slots, name="list_slots"),
    path("slots/new/", views.create_slot, name="create_slot"),
    path("slots/<int:slot_id>/edit/", views.edit_slot, name="edit_slot"),
    path("queue/<int:slot_id>/", views.monitor_queue, name="monitor_queue"),
    path("queue/approve/<int:token_id>/", views.approve_token, name="approve_token"),
    path("queue/skip/<int:token_id>/", views.skip_token, name="skip_token"),
    path("queue/serve/<int:token_id>/", views.serve_token, name="serve_token"),
    path("queue/reschedule/<int:token_id>/", views.reschedule_token, name="reschedule_token"),
    path("reports/summary/", views.reports_summary, name="reports_summary"),
]
