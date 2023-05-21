from django.contrib import admin
# <HINT> Import any new Models here
from . import models

# <HINT> Register QuestionInline and ChoiceInline classes here


class LessonInline(admin.StackedInline):
    model = models.Lesson
    extra = 2


# Register your models here.
class CourseAdmin(admin.ModelAdmin):
    inlines = [LessonInline]
    list_display = ('name', 'pub_date', 'id')
    list_filter = ['pub_date']
    search_fields = ['name', 'description']
    fields = ['name', 'image', 'description', 'pub_date', 'instructors']


class LessonAdmin(admin.ModelAdmin):
    list_display = ['title']
    fields = ['title', 'course', 'content']


class ChoiceInline(admin.StackedInline):
    model = models.Choice
    extra = 3

class QuestionAdmin(admin.ModelAdmin):
    inlines = [ChoiceInline]
    fields = ['lesson', 'text']

# <HINT> Register Question and Choice models here

admin.site.register(models.Course, CourseAdmin)
admin.site.register(models.Lesson, LessonAdmin)
admin.site.register(models.Instructor)
admin.site.register(models.Learner)
admin.site.register(models.Question, QuestionAdmin)
