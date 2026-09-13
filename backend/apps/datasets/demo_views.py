from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView


class RunDemoView(APIView):
    """
    POST /api/demo/run/
    Generates a synthetic multi-source study area (see demo/demo_data_generator.py),
    loads it as real Dataset rows + PostGIS features, and runs the full
    harmonization pipeline against it. Every number in the response is computed,
    not hard-coded.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from demo.demo_data_generator import DemoRunner
        runner = DemoRunner(user=request.user)
        result = runner.run_full_demo()
        return Response(result, status=status.HTTP_201_CREATED)
