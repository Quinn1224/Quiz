from django.db import models
from django.contrib.auth.models import User, Group
from django.utils import timezone
from django.core.exceptions import ValidationError


class Category(models.Model):
    """Modeliert eine Fragekategorie (z. B. Regelwerk)"""
    name = models.CharField(max_length=200, verbose_name='Name')
    description = models.TextField(blank=True, verbose_name='Beschreibung')
    last_modified = models.DateTimeField(auto_now=True, verbose_name='Zuletzt editiert')
    created = models.DateTimeField(auto_now_add=True, verbose_name='Erstellungszeitpunkt')
    class Meta:
        verbose_name = "Kategorie"
        verbose_name_plural = "Kategorien"


    def __str__(self):
        return self.name  
     
#Modeliert eine Frage
class Question(models.Model):
    """Modeliert eine Frage """
 
    OPTION_TYPES = [
        ('mutiple_choice', 'Multiple Choice (Text, Bild)'),
        ('multiple_choice_video', 'Multiple Choice (Video)'),
        ('draw_route', 'Laufroute/Zone einzeichnen'),
    ]
    text = models.CharField(max_length=1000, verbose_name='Fragetext')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, verbose_name='Kategorie')
    type = models.CharField(max_length=50, choices=OPTION_TYPES, default=OPTION_TYPES[0])
    points = models.SmallIntegerField(default=0, verbose_name='Punkte')
    image = models.ImageField(upload_to='quiz/questions/', null=True, blank=True, verbose_name='Bild')
    marked_for_review = models.BooleanField(default=False, verbose_name='Zur Prüfung markiert')
    interaction_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Interaktionsdaten'
    )

    last_modified = models.DateTimeField(auto_now=True, verbose_name='Zuletzt editiert')
    created = models.DateTimeField(auto_now_add=True, verbose_name='Erstellungszeitpunkt')

    class Meta:
        verbose_name = "Frage"
        verbose_name_plural = "Fragen"

    def __str__(self):
        return f"{self.text[:50]}"    

    def clean(self):
        super().clean()
        if self.type == 'mutiple_choice' and not self.image:
            raise ValidationError({'image': 'Für Multiple Choice (Bild) ist ein Bild erforderlich.'})

 #Modeliert eine Antwort
class Answer(models.Model):
    text = models.CharField(max_length=200, verbose_name='Antworttext')
    additional_information  = models.TextField(blank=True, verbose_name='Zusatzinformation')
    is_correct = models.BooleanField(default=False, verbose_name='Ist korrekt')
    related_question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    image = models.ImageField(upload_to='quiz/answers/', null=True, blank=True, verbose_name="Bild")
    last_modified = models.DateTimeField(auto_now=True, verbose_name='Zuletzt editiert')
    created = models.DateTimeField(auto_now_add=True, verbose_name='Erstellungszeitpunkt')
        
    class Meta:
        verbose_name = "Antwort"
        verbose_name_plural = "Antworten"

    def __str__(self):
        return f"{self.text} ({'Correct' if self.is_correct else 'False'})"     

# Modeliert den Fortschritt eines Nutzers für eine Frage
class QuestionProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_progress', verbose_name='Nutzer')   
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='question_progress')

    correct_attempts = models.PositiveIntegerField(default=0, verbose_name='Richtige Versuche')
    false_attempts = models.PositiveIntegerField(default=0, verbose_name='Falsche Versuche')
    last_answered = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'question')
        verbose_name = "Antwortfortschritt"
        verbose_name_plural = "Antwortfortschritte"

    def __str__(self):
        return f"{self.user.username} - Question {self.question.id} (Correct: {self.correct_attempts}, False: {self.false_attempts})"

    
class Statistics(models.Model):    
    """Modelliert die Statistik für einen bestimmten Nutzer"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_statistics')   
    total_score = models.PositiveBigIntegerField(default=0, verbose_name='Gesamtpunktzahl')

    @property
    def question_progress(self):
        return self.user.quiz_progress.all()
    
    class Meta:
        verbose_name="Nutzerstatistik"
        verbose_name_plural = "Nutzerstatistiken"

    def __str__(self):
        return f"{self.user.username} - Total Score: {self.total_score} "    


class QuestionGroup(models.Model):
    """Modeliert eine Fragegruppe, in der z. B. Testblöcke zusammengestellt werden können. Eine Frage kann Teil mehrere Gruppen sein"""
    title = models.CharField(max_length=200, verbose_name='Titel')
    description = models.CharField(max_length=1000, verbose_name='Beschreibung')
    is_published = models.BooleanField(
        default=False,
        verbose_name='Veröffentlichungsstatus',
        choices=[(True, 'Veröffentlicht'), (False, 'Unveröffentlicht')],
    )
    
    questions = models.ManyToManyField(
        Question,
        through='QuestionGroupItem',
        related_name='question_groups',
        verbose_name='Fragen'
    )

    user_group = models.ManyToManyField(
        Group,
        related_name='user_groups',
        verbose_name='Zugeordnete Nutzergruppe'
    )


    available_from = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Verfügbar ab'
    )

    due_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Verfügbar bis'
    )

    last_modified = models.DateTimeField(auto_now=True, verbose_name='Zuletzt editiert')
    created = models.DateTimeField(auto_now_add=True, verbose_name='Erstellungszeitpunkt')
    class Meta:
        verbose_name = 'Fragengruppe'
        verbose_name_plural = 'Fragengruppen'
        ordering = ['-created']

    def __str__(self):
        return self.title

    
class QuestionGroupItem(models.Model):
    """Zwischenmodell um eine Frage innerhalb einer Gruppe zu modellieren"""
    question_group = models.ForeignKey(
        QuestionGroup,
        on_delete=models.CASCADE,
        related_name='items'
    )

    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='group_items'
    )

    position = models.PositiveIntegerField(
        default=0,
        verbose_name='Position'
    )

    class Meta:
        ordering = ['position']
        constraints = [
            models.UniqueConstraint(
                fields=['question_group', 'question'],
                name='unique_question_per_group'
            ),
            models.UniqueConstraint(
                fields=['question_group', 'position'],
                name='unique_position_per_group'
            ),
        ]
        verbose_name = 'Frage in dieser Gruppe'
        verbose_name_plural = 'Fragen in dieser Gruppe'
    def __str__(self):
        return (
            f'{self.question_group.title}: '
            f'{self.position} - {self.question}'
        )
    