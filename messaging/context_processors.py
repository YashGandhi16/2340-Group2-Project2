from .models import Message


def unread_messages(request):
    """Expose the logged-in user's unread message count to every template."""
    if not request.user.is_authenticated:
        return {}
    return {'unread_message_count': Message.objects.unread_for(request.user).count()}
