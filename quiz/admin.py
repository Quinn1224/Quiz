from django.contrib import admin
from django import forms
from django.db import models
from django.forms.models import BaseInlineFormSet
from .models import Question, Answer, Category, QuestionProgress, Statistics, QuestionGroup, QuestionGroupItem

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


class QuestionGroupItemFormSet(BaseInlineFormSet):
    def add_fields(self, form, index):
        super().add_fields(form, index)

        if self.instance.pk:
            assigned_question_ids = self.model.objects.filter(
                **{self.fk.name: self.instance}
            ).values_list('question_id', flat=True)
            current_question_id = form.instance.question_id
            form.fields['question'].queryset = form.fields['question'].queryset.exclude(
                pk__in=assigned_question_ids
            )
            if current_question_id:
                form.fields['question'].queryset = (
                    form.fields['question'].queryset
                    | form.fields['question'].queryset.model.objects.filter(pk=current_question_id)
                )

            if index is not None and index >= self.initial_form_count():
                last_position = self.model.objects.filter(
                    **{self.fk.name: self.instance}
                ).aggregate(last_position=models.Max('position'))['last_position'] or 0
                form.initial['position'] = (
                    last_position + index - self.initial_form_count() + 1
                )

    def save_new(self, form, commit=True):
        obj = form.save(commit=False)
        last_position = self.model.objects.filter(
            **{self.fk.name: self.instance}
        ).aggregate(last_position=models.Max('position'))['last_position'] or 0
        obj.position = last_position + 1
        if commit:
            obj.save()
            self.save_m2m()
        return obj


class QuestionGroupItemInline(admin.TabularInline):
    model = QuestionGroupItem
    extra = 1
    fields = ('position', 'question')
    formset = QuestionGroupItemFormSet
    ordering = ('position',)

@admin.register(QuestionGroup)
class QuestionGroupAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'is_published',
        'question_count',
        'created',
    )

    list_filter = (
        'is_published',
        'created',
        'user_group',
    )

    search_fields = (
        'title',
        'description',
    )

    readonly_fields = (
        'created',
        'last_modified',
    )

    inlines = [QuestionGroupItemInline]
    filter_horizontal = ('user_group',)

    fieldsets = (
        ('Allgemeine Informationen', {
            'fields': (
                'title',
                'description',
                'user_group',
            ),
        }),
        ('Veröffentlichung', {
            'fields': (
                'is_published',
                'available_from',
                'due_date',
            ),
        }),
        ('Zeitstempel', {
            'fields': (
                'created',
                'last_modified',
            ),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Anzahl Fragen')
    def question_count(self, obj):
        return obj.questions.count()


admin.site.register(Category)
admin.site.register(QuestionProgress)
admin.site.register(Statistics)