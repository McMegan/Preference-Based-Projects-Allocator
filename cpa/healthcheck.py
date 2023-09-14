from django.http import JsonResponse

from health_check.views import MainView


class HealthCheckView(MainView):
    def get(self, request, *args, **kwargs):
        status_code = 500 if self.errors else 200
        return self.render_to_response_json(self.plugins, status_code)

    def render_to_response_json(self, plugins, status):
        return JsonResponse(
            data={**{str(p.identifier()): str(p.pretty_status())
                     for p in plugins}, 'status': status},
            status=status,
        )
