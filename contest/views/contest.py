from django import forms
from django.contrib.auth import mixins as authmixins
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views import generic
from django.views.generic.detail import SingleObjectMixin

from contest import models


class Index(generic.ListView):
    template_name = 'jam/index.html'
    model = models.Problem


class ScoreBoard(generic.ListView):
    template_name = 'jam/scoreboard.html'
    model = User

    def get_queryset(self):
        for score in models.Score.objects.all():
            score.recompute()
        return User.objects.filter(score__points__gt=0).order_by('-score__points')


class ProblemDetail(generic.DetailView):
    model = models.Problem
    template_name = 'jam/problem.html'


class ProblemCreate(authmixins.PermissionRequiredMixin, generic.CreateView):
    permission_required = 'contest.add_problem'

    model = models.Problem
    template_name = 'jam/problem_create.html'

    fields = 'title', 'slug', 'description'


class ProblemDelete(authmixins.PermissionRequiredMixin, generic.DeleteView):
    permission_required = 'contest.delete_problem'

    model = models.Problem
    success_url = reverse_lazy('contest:index')


class ProblemUpdate(authmixins.PermissionRequiredMixin, generic.UpdateView):
    permission_required = 'contest.update_problem'

    model = models.Problem
    template_name = 'jam/problem_update.html'

    fields = 'title', 'description'


class PartCreate(authmixins.PermissionRequiredMixin, generic.CreateView):
    permission_required = 'contest.create_part'

    model = models.Part
    template_name = 'jam/part_create.html'

    fields = 'title', 'slug', 'points', 'input', 'solution'

    def get_context_data(self, **kwargs):
        ctx = super(PartCreate, self).get_context_data(**kwargs)
        ctx['problem'] = models.Problem.objects.get(slug=self.kwargs['slug'])
        return ctx

    def form_valid(self, form):
        form.instance.problem = models.Problem.objects.get(slug=self.kwargs['slug'])
        return super(PartCreate, self).form_valid(form)


class PartCreateUpload(authmixins.PermissionRequiredMixin, generic.CreateView):
    permission_required = 'contest.create_part'

    model = models.Part
    template_name = 'jam/part_create_upload.html'

    form_class = forms.modelform_factory(
        models.Part,
        fields=('title', 'slug', 'points', 'input', 'solution'),
        field_classes=(
            forms.CharField, forms.SlugField, forms.IntegerField, forms.FileField,
            forms.FileField)
    )

    def get_form(self, form_class=None):
        cls = form_class or self.get_form_class()
        return cls(self.request.POST, self.request.FILES)

    def get_context_data(self, **kwargs):
        ctx = super(PartCreateUpload, self).get_context_data(**kwargs)
        ctx['problem'] = models.Problem.objects.get(slug=self.kwargs['slug'])
        return ctx

    def form_valid(self, form):
        form.instance.problem = models.Problem.objects.get(slug=self.kwargs['slug'])
        form.instance.input = form.files['input'].read().decode('utf-8')
        form.instance.solution = form.files['solution'].read().decode('utf-8')

        return super(PartCreateUpload, self).form_valid(form)


class PartDelete(authmixins.PermissionRequiredMixin, generic.DeleteView):
    permission_required = 'contest.delete_part'

    model = models.Part

    def get_success_url(self):
        return reverse_lazy('contest:problem', kwargs=dict(slug=self.kwargs['problem']))


class PartUpdate(authmixins.PermissionRequiredMixin, generic.UpdateView):
    permission_required = 'contest.update_part'

    model = models.Part
    template_name = 'jam/part_update.html'

    fields = 'title', 'slug', 'points', 'input', 'solution'

    def get_context_data(self, **kwargs):
        ctx = super(PartUpdate, self).get_context_data(**kwargs)
        ctx['problem'] = models.Problem.objects.get(slug=self.kwargs['problem'])
        return ctx

    def form_valid(self, form):
        form.instance.problem = models.Problem.objects.get(slug=self.kwargs['problem'])
        return super(PartUpdate, self).form_valid(form)


class PartDownload(SingleObjectMixin, generic.View):
    model = models.Part

    def get(self, request, *args, **kwargs):
        part = self.get_object()
        return HttpResponse(part.input, content_type='text/plain; charset=utf8')


class PartSubmit(authmixins.LoginRequiredMixin, generic.FormView):
    template_name = 'jam/part_submit.html'

    form_class = forms.modelform_factory(models.Submission, fields=('submission',))

    def get_context_data(self, **kwargs):
        ctx = super(PartSubmit, self).get_context_data(**kwargs)
        ctx['problem'] = models.Problem.objects.get(slug=self.kwargs['problem'])
        ctx['part'] = models.Part.objects.get(pk=self.kwargs['pk'])
        return ctx

    def form_valid(self, form):
        form.instance.part = models.Part.objects.get(pk=self.kwargs['pk'])
        form.instance.user = User.objects.get(id=self.request.user.id)
        form.instance.submission = form.cleaned_data['submission']

        form.instance.save()

        self.submission = form.instance

        return super(PartSubmit, self).form_valid(form)

    def get_success_url(self):
        return self.submission.get_absolute_url()


class PartSubmitUpload(PartSubmit):
    template_name = 'jam/part_submit_upload.html'

    class form_class(forms.Form):
        submission = forms.FileField()

    def get_form(self, form_class=None):
        cls = form_class or self.get_form_class()
        return cls(self.request.POST, self.request.FILES)

    def form_valid(self, form):
        f = form.files['submission']
        form.instance = models.Submission.objects.create(
            part=models.Part.objects.get(pk=self.kwargs['pk']),
            user=User.objects.get(id=self.request.user.id),
            submission=f.read().decode('utf-8')
        )

        form.instance.save()

        self.submission = form.instance

        return generic.FormView.form_valid(self, form)


class SubmissionDetail(generic.DetailView):
    model = models.Submission
    template_name = 'jam/submission.html'


class SubmissionList(authmixins.LoginRequiredMixin, generic.ListView):
    model = models.Submission
    template_name = 'jam/submissions.html'

    def get_queryset(self):
        return self.model.objects.filter(user__exact=self.request.user)