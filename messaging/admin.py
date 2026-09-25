from django.contrib import admin

from .models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('sender', 'body', 'sent_at', 'read_at')


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('recruiter', 'candidate', 'updated_at')
    search_fields = ('recruiter__username', 'candidate__username')
    inlines = [MessageInline]
