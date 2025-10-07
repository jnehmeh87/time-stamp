import stripe
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import redirect
from .models import Subscription, SubscriptionPlan
from users.models import Organization
from django.utils import timezone
from datetime import datetime

stripe.api_key = settings.STRIPE_SECRET_KEY

def create_checkout_session(request, plan_id):
    plan = SubscriptionPlan.objects.get(id=plan_id)
    organization = request.user.organizations.first()

    if not organization:
        return redirect('workspaces:home')

    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': plan.name,
                },
                'unit_amount': int(plan.price * 100),
                'recurring': {
                    'interval': 'month',
                },
            },
            'quantity': 1,
        }],
        mode='subscription',
        success_url=request.build_absolute_uri('/subscriptions/success/'),
        cancel_url=request.build_absolute_uri('/subscriptions/cancel/'),
        client_reference_id=organization.id,
    )

    return JsonResponse({'id': session.id})

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return HttpResponse(status=400)

    # Handle the checkout.session.completed event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        client_reference_id = session.get('client_reference_id')
        if client_reference_id:
            organization = Organization.objects.get(id=client_reference_id)
            subscription_id = session.get('subscription')
            stripe_subscription = stripe.Subscription.retrieve(subscription_id)
            plan_id = stripe_subscription['plan']['id']
            plan = SubscriptionPlan.objects.get(stripe_plan_id=plan_id)
            
            # Create or update the subscription
            subscription, created = Subscription.objects.update_or_create(
                organization=organization,
                defaults={
                    'plan': plan,
                    'start_date': timezone.now(),
                    'end_date': timezone.make_aware(datetime.fromtimestamp(stripe_subscription['current_period_end'])),
                    'is_active': True,
                }
            )

    return HttpResponse(status=200)