from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .reports_service import ReportGenerationService


class GenerateReportView(APIView):
    """
    Generate a report for a specific client's social media page.
    Query params:
    - client_id: ID of the client
    - page_id: ID of the social media page
    - report_type: 'week' or 'month'
    - period: Start date in format 'YYYY-MM-DD' (for week) or 'YYYY-MM' (for month)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get query parameters
        client_id = request.query_params.get("client_id")
        page_id = request.query_params.get("page_id")
        report_type = request.query_params.get("report_type", "week")
        period = request.query_params.get("period")

        # Validate required parameters
        if not all([client_id, page_id, period]):
            return Response(
                {"error": "client_id, page_id, and period are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Use service to generate report
            report_data = ReportGenerationService.generate_report(
                client_id=int(client_id),
                page_id=int(page_id),
                report_type=report_type,
                period=period,
            )

            return Response(report_data, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
