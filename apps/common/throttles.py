"""Anonymous throttle classes used by public write endpoints.

Scope names line up with `DEFAULT_THROTTLE_RATES` in
core/settings/base.py.
"""

from rest_framework.throttling import AnonRateThrottle


class EnquiryThrottle(AnonRateThrottle):
    """10/hour per IP. Tighter than the generic anon rate (60/hour)
    because POST /api/v1/enquiries/ is a public write endpoint that
    triggers an email — spam protection matters here."""

    scope = "enquiry"
