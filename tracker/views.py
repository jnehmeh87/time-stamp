from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.urls import reverse
from workspaces.models import TimeEntry, Project
from .forms import ReportForm
from django.contrib import messages
from django.db.models import Sum, F, Min, Max
from django.http import JsonResponse
from datetime import timedelta, date, datetime, time
from decimal import Decimal, InvalidOperation
from collections import defaultdict
import csv
from googletrans import Translator, LANGUAGES
from .utils import render_to_pdf
