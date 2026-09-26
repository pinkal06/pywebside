from django import forms
from django.conf import settings

from .models import Message


class MessageForm(forms.ModelForm):
    audio_file = forms.FileField(required=False, widget=forms.FileInput(attrs={"accept": "audio/webm,audio/ogg,audio/mp4"}))
    def clean_body(self):
        body = self.cleaned_data.get("body", "").strip()
        if not body and not self.files.get("audio_file"):
            raise forms.ValidationError("Message cannot be empty.")
        return body

    def clean_audio_file(self):
        audio = self.cleaned_data.get("audio_file")
        if audio:
            if audio.size > settings.CHAT_MAX_AUDIO_SIZE:
                raise forms.ValidationError("Voice message is too large.")
            if audio.content_type not in {"audio/webm", "audio/ogg", "audio/mp4", "audio/mpeg"}:
                raise forms.ValidationError("Unsupported voice message format.")
        return audio

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("audio_file"):
            cleaned["message_type"] = Message.TYPE_VOICE
            cleaned["body"] = ""
        return cleaned

    class Meta:
        model = Message
        fields = ("body", "audio_file")
        widgets = {"body": forms.Textarea(attrs={"rows": 3, "maxlength": 2000, "placeholder": "Write a message...", "aria-label": "Message"})}
