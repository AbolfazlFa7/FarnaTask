import time
from django.db import connection
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.utils.termcolors import colorize
from django.utils import timezone


class QueryLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log all SQL queries for each request in DEBUG mode.
    Prevents duplicate logs and handles both success and error responses.
    """

    def process_request(self, request):
        if settings.DEBUG:
            request._query_start_time = time.monotonic()
            request._query_logger_done = False
        return None

    def process_response(self, request, response):
        # Skip if not DEBUG
        if not settings.DEBUG:
            return response

        # Prevent duplicate logging
        if getattr(request, "_query_logger_done", False):
            return response
        request._query_logger_done = True

        just_count = getattr(settings, "QUERY_LOGGER_JUST_COUNT", False)

        total_time = (time.monotonic() - getattr(request,
                      "_query_start_time", time.monotonic())) * 1000
        queries = connection.queries
        query_count = len(queries)
        total_db_time = sum(float(q.get("time", 0)) * 1000 for q in queries)

        # Colors
        def cyan(s): return colorize(s, fg="cyan")
        def yellow(s): return colorize(s, fg="yellow")
        def green(s): return colorize(s, fg="green")
        def magenta(s): return colorize(s, fg="magenta")
        def red(s): return colorize(s, fg="red")

        print("\n" + "=" * 100)
        print(
            green(
                f"🧩 Query Report for {request.path} [{request.method}] at {timezone.now().strftime('%H:%M:%S')}"
            )
        )
        print(
            yellow(
                f"Total Queries: {query_count} | Total DB Time: {total_db_time:.2f} ms | Total Request Time: {total_time:.2f} ms"
            )
        )
        print("-" * 100)

        if not just_count:
            for idx, query in enumerate(queries, start=1):
                sql = query["sql"]
                time_taken = float(query.get("time", 0)) * 1000
                print(f"{cyan(f'[{idx}]')} {
                      magenta(f'{time_taken:.2f} ms')} → {sql}")
        else:
            print(cyan("🔹 Skipping query details (QUERY_LOGGER_JUST_COUNT=True)"))

        if query_count == 0:
            print(red("⚠️ No database queries were executed in this request."))

        print("=" * 100 + "\n")

        return response

    def process_exception(self, request, exception):
        """
        Ensure that even if an exception occurs, the query log prints once.
        """
        # Call process_response manually if not done
        if settings.DEBUG and not getattr(request, "_query_logger_done", False):
            # Fake a dummy response to trigger logging
            from django.http import HttpResponseServerError
            dummy_response = HttpResponseServerError()
            return self.process_response(request, dummy_response)
        return None
