from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponse
# <HINT> Import any new Models here
from .models import Course, Enrollment
from . import models
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import generic
from django.contrib.auth import login, logout, authenticate
import logging
# Get an instance of a logger
logger = logging.getLogger(__name__)
# Create your views here.


def registration_request(request):
    context = {}
    if request.method == 'GET':
        return render(request, 'onlinecourse/user_registration_bootstrap.html', context)
    elif request.method == 'POST':
        # Check if user exists
        username = request.POST['username']
        password = request.POST['psw']
        first_name = request.POST['firstname']
        last_name = request.POST['lastname']
        user_exist = False
        try:
            User.objects.get(username=username)
            user_exist = True
        except:
            logger.error("New user")
        if not user_exist:
            user = User.objects.create_user(username=username, first_name=first_name, last_name=last_name,
                                            password=password)
            login(request, user)
            return redirect("onlinecourse:index")
        else:
            context['message'] = "User already exists."
            return render(request, 'onlinecourse/user_registration_bootstrap.html', context)


def login_request(request):
    context = {}
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['psw']
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('onlinecourse:index')
        else:
            context['message'] = "Invalid username or password."
            return render(request, 'onlinecourse/user_login_bootstrap.html', context)
    else:
        return render(request, 'onlinecourse/user_login_bootstrap.html', context)


def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')


def check_if_enrolled(user, course):
    is_enrolled = False
    if user.id is not None:
        # Check if user enrolled
        num_results = Enrollment.objects.filter(user=user, course=course).count()
        if num_results > 0:
            is_enrolled = True
    return is_enrolled


# CourseListView
class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        user = self.request.user
        courses = Course.objects.order_by('-total_enrollment')[:10]
        for course in courses:
            if user.is_authenticated:
                course.is_enrolled = check_if_enrolled(user, course)
        return courses


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_detail_bootstrap.html'

    def get_object(self, queryset=None):
        pk = self.kwargs.get('pk') # get the pk passed from the url
        return super().get_object(queryset=queryset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs) # get the default context dictionary
        lessons = models.Lesson.objects.filter(course_id=self.object.pk)
        lesson_pks = [lesson.pk for lesson in lessons]
        questions = models.Question.objects.filter(lesson__in=lesson_pks).distinct()
        context['questions'] = questions # add additional data to the context dictionary

        user = self.request.user
        course = get_object_or_404(Course, pk=self.object.pk)
        is_enrolled = check_if_enrolled(user, course)
        context['is_enrolled'] = is_enrolled

        return context


def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    is_enrolled = check_if_enrolled(user, course)
    if not is_enrolled and user.is_authenticated:
        # Create an enrollment
        Enrollment.objects.create(user=user, course=course, mode='honor')
        course.total_enrollment += 1
        course.save()

    return HttpResponseRedirect(reverse(viewname='onlinecourse:course_details', args=(course.id,)))


# <HINT> Create a submit view to create an exam submission record for a course enrollment,
# you may implement it based on following logic:
         # Get user and course object, then get the associated enrollment object created when the user enrolled the course
         # Create a submission object referring to the enrollement
         # Collect the selected choices from exam form
         # Add each selected choice object to the submission object
         # Redirect to show_exam_result with the submission id
def submit(request, course_id):
    user_id = request.user.id
    # I have to enroll first, otherwise, the following throws an error
    # I should consider the cases of accessing without enrolling (to avoid errors)
    enrollment = models.Enrollment.objects.get(course_id=course_id, user_id=user_id)
    submission = models.Submission.objects.create(enrollment=enrollment)
    Ids = extract_checked_answers_Ids(request)
    choices = models.Choice.objects.filter(id__in=Ids)
    submission.choices.set(choices)
    submission.save()
    return redirect(reverse('onlinecourse:result', kwargs={'course_id':course_id, 'submission_id': submission.id}))


# <HINT> A example method to collect the selected choices from the exam form from the request object
def extract_checked_answers_Ids(request):
   '''
   Only returns the Ids of checked inputs
   '''
   submitted_anwsers = []
   for key in request.POST:
       # the keys are the names given in the input tag in the template
       if key.startswith('choice'):
           value = request.POST[key]
           choice_id = int(value)
           submitted_anwsers.append(choice_id)
   return submitted_anwsers


# <HINT> Create an exam result view to check if learner passed exam and show their question results and result for each question,
# you may implement it based on the following logic:
        # Get course and submission based on their ids
        # Get the selected choice ids from the submission record
        # For each selected choice, check if it is a correct answer or not
        # Calculate the total score
def show_exam_result(request, course_id, submission_id):
    submission = models.Submission.objects.get(id=submission_id)
    checked_choices = models.Choice.objects.filter(submission=submission_id).values_list('id', flat=True)
    lesson_ids = models.Lesson.objects.filter(course_id=course_id).values_list('id', flat=True)
    questions = models.Question.objects.filter(lesson__in=lesson_ids)
    exam_grade = 0
    success = False
    associated_choices = {}
    for question in questions:
        '''
        This loop (or the grading in general) should be subjects to optimization
        '''
        correct_choices, incorrect_choices = [], []
        # associated choices for each question
        associated_choices[question.id] = submission.choices.filter(question=question)
        for choice in question.choice_set.all():
            if choice.is_correct: correct_choices.append(choice.id)
            else: incorrect_choices.append(choice.id)
        # the retrieved choices should include the first list and none of the second (use a set for intersection)
        # if set(correct_choices).issubset(checked_choices) and not set(incorrect_choices).issubset(checked_choices):
        if set(correct_choices).issubset(checked_choices) and set(incorrect_choices).isdisjoint(checked_choices):
            question.grade = 1
            exam_grade+=1
    exam_grade = exam_grade/len(questions) * 100
    
    return render(
        request, 'onlinecourse/exam_result_bootstrap.html', {
            'questions': questions, 'course_id': course_id, 'associated_choices': associated_choices, 'exam_grade': exam_grade
            }
        )




