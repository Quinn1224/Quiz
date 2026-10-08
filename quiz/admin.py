from django.contrib import admin
from django import forms
from django.db import models
from .models import Question, Answer, Category, QuestionProgress, Statistics

# Register your models here.
class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 1
    min_num = 2
    formfield_overrides = {
        models.TextField: {'widget': forms.Textarea(attrs={'rows': 4})},
        models.CharField: {'widget': forms.Textarea(attrs={'rows': 2})}
    }

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'category', 'type', 'points' ,'last_modified', 'created', 'marked_for_review')
    list_filter = ('category', 'type', 'marked_for_review')
    search_fields = ('text',)
    inlines = [AnswerInline]
    formfield_overrides = {
        models.CharField: {'widget': forms.Textarea(attrs={'rows': 2, 'cols': 80})},
    }

admin.site.register(Category)
admin.site.register(QuestionProgress)
admin.site.register(Statistics)