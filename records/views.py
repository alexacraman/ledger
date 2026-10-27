from decimal import Decimal, ROUND_HALF_UP

from django.shortcuts import render
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.db.models import Sum
from django.db.models.functions import ExtractMonth

from membership.utils import CommitteeRequiredMixin

from .models import Record
from .forms import RecordForm
from .forms_reports import WorkReportForm
from .reporting import build_work_report
from .utils import format_duration

from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Sum
from django.db.models.functions import ExtractMonth
from django.views.generic import ListView

from .models import Record
from .utils import format_duration



from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Sum
from django.db.models.functions import ExtractMonth, ExtractYear
from django.views.generic import ListView

class RecordListView(CommitteeRequiredMixin, LoginRequiredMixin, ListView):
    model = Record
    template_name = 'records/record_list.html'
    context_object_name = 'records'
    paginate_by = 6

    def get_queryset(self):
        queryset = Record.objects.filter(user=self.request.user).order_by('date')

        self.selected_year = self.request.GET.get('year', '')
        self.selected_month = self.request.GET.get('month', '')

        if self.selected_year.isdigit():
            year = int(self.selected_year)
            if 1900 <= year <= 9999:
                queryset = queryset.filter(date__year=year)

        if self.selected_month.isdigit():
            month = int(self.selected_month)
            if 1 <= month <= 12:
                queryset = queryset.filter(date__month=month)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user_records = Record.objects.filter(user=self.request.user)

        active_years = (
            user_records
            .annotate(year=ExtractYear('date'))
            .values_list('year', flat=True)
            .distinct()
            .order_by('-year')
        )

        active_months = (
            user_records
            .annotate(month=ExtractMonth('date'))
            .values_list('month', flat=True)
            .distinct()
            .order_by('month')
        )

        month_names = {
            1: 'January', 2: 'February', 3: 'March',
            4: 'April', 5: 'May', 6: 'June',
            7: 'July', 8: 'August', 9: 'September',
            10: 'October', 11: 'November', 12: 'December',
        }

        context['available_years'] = active_years
        context['available_months'] = [
            {'value': month, 'name': month_names[month]}
            for month in active_months
        ]

        context['selected_year'] = (
            int(self.selected_year)
            if self.selected_year.isdigit()
            and 1900 <= int(self.selected_year) <= 9999
            else ''
        )

        context['selected_month'] = (
            int(self.selected_month)
            if self.selected_month.isdigit()
            and 1 <= int(self.selected_month) <= 12
            else ''
        )

        # Calculate completed hours across all matching records,
        # not just the current page.
        total_hours = self.get_queryset().filter(
            status='COMPLETED'
        ).aggregate(total=Sum('duration_hours'))['total']

        total_completed_hours = (
            Decimal(total_hours).quantize(
                Decimal('0.01'),
                rounding=ROUND_HALF_UP
            )
            if total_hours is not None
            else Decimal('0.00')
        )

        context['total_completed_hours'] = format_duration(
            total_completed_hours
        )

        return context

    
class RecordCreateView(CommitteeRequiredMixin,LoginRequiredMixin, CreateView):
    model = Record
    form_class = RecordForm
    template_name = 'records/record_form.html'
    success_url = reverse_lazy('record:record_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)




class RecordUpdateView(CommitteeRequiredMixin, LoginRequiredMixin, UpdateView):
    model = Record
    form_class = RecordForm
    template_name = 'records/record_form.html'

    def get_queryset(self):
        return Record.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_no'] = self.request.POST.get('page') or self.request.GET.get('page', '')
        context['selected_year'] = self.request.POST.get('year') or self.request.GET.get('year', '')
        context['selected_month'] = self.request.POST.get('month') or self.request.GET.get('month', '')
        return context

    def get_success_url(self):
        page = self.request.POST.get('page') or self.request.GET.get('page')
        year = self.request.POST.get('year') or self.request.GET.get('year')
        month = self.request.POST.get('month') or self.request.GET.get('month')

        params = []

        if page and page.isdigit() and int(page) > 0:
            params.append(f'page={page}')

        if year and year.isdigit():
            params.append(f'year={year}')

        if month and month.isdigit() and 1 <= int(month) <= 12:
            params.append(f'month={month}')

        url = reverse('record:record_list')
        return f"{url}?{'&'.join(params)}" if params else url


class RecordDeleteView(CommitteeRequiredMixin,LoginRequiredMixin, DeleteView):
    model = Record
    template_name = 'records/record_confirm_delete.html'
    success_url = reverse_lazy('record:record_list')

    def get_queryset(self):
        return Record.objects.filter(user=self.request.user)


class WorkReportView(CommitteeRequiredMixin, LoginRequiredMixin, View):
    template_name = "records/report_form.html"

    def get(self, request, *args, **kwargs):
        if request.GET.get("generate") == "1":
            form = WorkReportForm(request.GET)

            if form.is_valid():
                start_date = form.cleaned_data["start_date"]
                end_date = form.cleaned_data["end_date"]
                monthly_allowance = form.cleaned_data["monthly_allowance"]

                records = Record.objects.filter(
                    user=request.user,
                    date__range=(start_date, end_date),
                ).order_by("date", "created_at")

                return build_work_report(
                    records=records,
                    start_date=start_date,
                    end_date=end_date,
                    monthly_allowance=monthly_allowance,
                )
        else:
            form = WorkReportForm()

        return render(request, self.template_name, {"form": form})
