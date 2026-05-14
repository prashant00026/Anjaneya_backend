from rest_framework import generics, permissions

from common.throttles import EnquiryThrottle

from .models import Enquiry
from .serializers import EnquiryCreateSerializer


def _client_ip(request):
    # TODO: when we sit behind a trusted reverse proxy, honour the
    # left-most X-Forwarded-For only after verifying the connecting
    # peer is in a trusted list. Until then, REMOTE_ADDR is the only
    # source we can trust.
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class EnquiryCreateView(generics.CreateAPIView):
    """Public POST-only endpoint. Reads happen via Django admin."""

    queryset = Enquiry.objects.all()
    serializer_class = EnquiryCreateSerializer
    permission_classes = (permissions.AllowAny,)
    throttle_classes = (EnquiryThrottle,)

    def perform_create(self, serializer):
        serializer.save(
            ip_address=_client_ip(self.request),
            user_agent=self.request.META.get("HTTP_USER_AGENT", "")[:255],
        )
