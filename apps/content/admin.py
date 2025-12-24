from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.utils import timezone
from django.db.models import Count, Q, Avg, F
from django.template.response import TemplateResponse
from django.shortcuts import render
from datetime import timedelta
from .models import Post, Media


class ContentAdminSite(admin.ModelAdmin):
    """Custom admin site with statistics dashboard"""

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "content-stats/",
                self.admin_site.admin_view(self.content_stats_view),
                name="content_stats",
            ),
        ]
        return custom_urls + urls

    def content_stats_view(self, request):
        """Custom view for content statistics"""
        # Calculate time periods
        now = timezone.now()
        last_7_days = now - timedelta(days=7)
        last_30_days = now - timedelta(days=30)
        last_90_days = now - timedelta(days=90)

        # Overall post statistics
        total_posts = Post.objects.count()
        posts_last_7_days = Post.objects.filter(created_at__gte=last_7_days).count()
        posts_last_30_days = Post.objects.filter(created_at__gte=last_30_days).count()

        # Status breakdown
        status_stats = (
            Post.objects.values("status").annotate(count=Count("id")).order_by("-count")
        )

        # Workflow efficiency stats
        published_posts = Post.objects.filter(status="published")
        avg_workflow_time = None
        if published_posts.exists():
            # Calculate average time from creation to publication
            workflow_times = []
            for post in published_posts.filter(published_at__isnull=False):
                if post.published_at and post.created_at:
                    workflow_time = (
                        post.published_at - post.created_at
                    ).total_seconds() / 3600  # in hours
                    workflow_times.append(workflow_time)

            if workflow_times:
                avg_workflow_time = sum(workflow_times) / len(workflow_times)

        # User activity stats
        top_creators = (
            Post.objects.values(
                "creator__email", "creator__first_name", "creator__last_name"
            )
            .annotate(post_count=Count("id"))
            .order_by("-post_count")[:10]
        )

        # Client activity stats
        top_clients = (
            Post.objects.values(
                "client__email", "client__first_name", "client__last_name"
            )
            .annotate(post_count=Count("id"))
            .order_by("-post_count")[:10]
        )

        # Approval rates
        total_pending_or_higher = Post.objects.filter(
            status__in=["pending", "scheduled", "published", "rejected"]
        ).count()

        approved_posts = Post.objects.filter(is_client_approved=True).count()
        validated_posts = Post.objects.filter(is_moderator_validated=True).count()
        rejected_posts = Post.objects.filter(status="rejected").count()

        client_approval_rate = (
            (approved_posts / total_pending_or_higher * 100)
            if total_pending_or_higher > 0
            else 0
        )
        moderator_validation_rate = (
            (validated_posts / total_pending_or_higher * 100)
            if total_pending_or_higher > 0
            else 0
        )
        rejection_rate = (
            (rejected_posts / total_pending_or_higher * 100)
            if total_pending_or_higher > 0
            else 0
        )

        # Media statistics
        total_media = Media.objects.count()
        media_by_type = Media.objects.values("type").annotate(count=Count("id"))
        unused_media = Media.objects.filter(posts__isnull=True).count()

        # Recent activity
        recent_posts = Post.objects.select_related("creator", "client").order_by(
            "-updated_at"
        )[:10]

        # Performance metrics
        posts_needing_attention = Post.objects.filter(
            Q(status="pending") & Q(created_at__lt=now - timedelta(days=3))
        ).count()

        overdue_posts = Post.objects.filter(
            Q(scheduled_for__lt=now) & Q(status="scheduled")
        ).count()

        context = {
            "title": "Content Statistics Dashboard",
            "total_posts": total_posts,
            "posts_last_7_days": posts_last_7_days,
            "posts_last_30_days": posts_last_30_days,
            "status_stats": status_stats,
            "avg_workflow_time": avg_workflow_time,
            "top_creators": top_creators,
            "top_clients": top_clients,
            "client_approval_rate": round(client_approval_rate, 2),
            "moderator_validation_rate": round(moderator_validation_rate, 2),
            "rejection_rate": round(rejection_rate, 2),
            "total_media": total_media,
            "media_by_type": media_by_type,
            "unused_media": unused_media,
            "recent_posts": recent_posts,
            "posts_needing_attention": posts_needing_attention,
            "overdue_posts": overdue_posts,
            "approved_posts": approved_posts,
            "validated_posts": validated_posts,
            "rejected_posts": rejected_posts,
        }

        return TemplateResponse(request, "admin/content_stats.html", context)


class MediaAdmin(admin.ModelAdmin):
    model = Media
    list_display = (
        "name",
        "type",
        "creator",
        "file_size_display",
        "uploaded_at",
        "posts_count",
    )
    list_filter = ("type", "uploaded_at", "creator")
    search_fields = ("name", "file__name", "creator__email")
    readonly_fields = ("uploaded_at", "file_size_display", "posts_count")
    ordering = ("-uploaded_at",)

    def file_size_display(self, obj):
        """Display file size in human readable format"""
        if obj.file:
            try:
                size = obj.file.size
                for unit in ["B", "KB", "MB", "GB"]:
                    if size < 1024.0:
                        return f"{size:.1f} {unit}"
                    size /= 1024.0
                return f"{size:.1f} TB"
            except:
                return "Unknown"
        return "No file"

    file_size_display.short_description = "File Size"

    def posts_count(self, obj):
        """Display number of posts using this media"""
        count = obj.posts.count()
        if count > 0:
            url = (
                reverse("admin:content_post_changelist") + f"?media__id__exact={obj.id}"
            )
            return format_html('<a href="{}">{} posts</a>', url, count)
        return "0 posts"

    posts_count.short_description = "Used in Posts"


class PostAdmin(ContentAdminSite):
    model = Post
    list_display = (
        "title",
        "creator",
        "client",
        "status",
        "created_at",
        "updated_at",
        "last_edited_by",
        "scheduled_for",
        "workflow_status",
        "days_since_creation",
    )
    list_filter = (
        "status",
        "created_at",
        "updated_at",
        "is_client_approved",
        "is_moderator_validated",
        "creator",
        "client",
        "last_edited_by",
    )
    search_fields = ("title", "description", "creator__email", "client__email")
    readonly_fields = (
        "created_at",
        "updated_at",
        "workflow_timeline",
        "change_history",
        "time_in_workflow",
        "total_revisions",
    )

    def changelist_view(self, request, extra_context=None):
        """Add statistics to the changelist view"""
        # Calculate statistics for the changelist
        total_posts = self.get_queryset(request).count()

        # Status distribution
        status_counts = {}
        for status_choice in Post.STATUS_CHOICES:
            status_key = status_choice[0]
            status_counts[status_choice[1]] = (
                self.get_queryset(request).filter(status=status_key).count()
            )

        # Recent activity (last 7 days)
        last_7_days = timezone.now() - timedelta(days=7)
        recent_posts = (
            self.get_queryset(request).filter(created_at__gte=last_7_days).count()
        )

        # Posts needing attention
        posts_needing_attention = (
            self.get_queryset(request)
            .filter(
                Q(status="pending")
                & Q(created_at__lt=timezone.now() - timedelta(days=3))
            )
            .count()
        )

        # Workflow efficiency
        avg_approval_time = (
            self.get_queryset(request)
            .filter(client_approved_at__isnull=False)
            .aggregate(avg_time=Avg(F("client_approved_at") - F("created_at")))[
                "avg_time"
            ]
        )

        extra_context = extra_context or {}
        extra_context.update(
            {
                "total_posts": total_posts,
                "status_counts": status_counts,
                "recent_posts": recent_posts,
                "posts_needing_attention": posts_needing_attention,
                "avg_approval_time": avg_approval_time.days
                if avg_approval_time
                else None,
                "stats_url": reverse("admin:content_stats"),
            }
        )

        return super().changelist_view(request, extra_context=extra_context)

    model = Post
    list_display = (
        "title",
        "creator",
        "client",
        "status",
        "created_at",
        "updated_at",
        "last_edited_by",
        "scheduled_for",
        "workflow_status",
        "days_since_creation",
    )
    list_filter = (
        "status",
        "created_at",
        "updated_at",
        "is_client_approved",
        "is_moderator_validated",
        "creator",
        "client",
        "last_edited_by",
    )
    search_fields = ("title", "description", "creator__email", "client__email")
    readonly_fields = (
        "created_at",
        "updated_at",
        "workflow_timeline",
        "change_history",
        "time_in_workflow",
        "total_revisions",
    )

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("title", "description", "creator", "client")},
        ),
        (
            "Scheduling & Publishing",
            {"fields": ("scheduled_for", "status", "platforms", "platform_page")},
        ),
        ("Media", {"fields": ("media",)}),
        (
            "Workflow Status",
            {
                "fields": (
                    "is_client_approved",
                    "is_moderator_validated",
                    "feedback",
                    "feedback_by",
                    "feedback_at",
                )
            },
        ),
        (
            "Tracking Information",
            {
                "fields": (
                    "last_edited_by",
                    "created_at",
                    "updated_at",
                    "workflow_timeline",
                    "change_history",
                    "time_in_workflow",
                    "total_revisions",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Workflow Timestamps",
            {
                "fields": (
                    "client_approved_at",
                    "client_rejected_at",
                    "moderator_validated_at",
                    "moderator_rejected_at",
                    "published_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    filter_horizontal = ("media",)
    ordering = ("-updated_at",)
    date_hierarchy = "created_at"

    def workflow_status(self, obj):
        """Display workflow status with color coding"""
        status_colors = {
            "draft": "#6c757d",  # Gray
            "pending": "#ffc107",  # Yellow
            "rejected": "#dc3545",  # Red
            "scheduled": "#17a2b8",  # Cyan
            "published": "#28a745",  # Green
            "failed": "#dc3545",  # Red
        }

        color = status_colors.get(obj.status, "#6c757d")

        # Add workflow indicators
        indicators = []
        if obj.is_client_approved:
            indicators.append("✓ Client")
        elif obj.is_client_approved is False:
            indicators.append("✗ Client")

        if obj.is_moderator_validated:
            indicators.append("✓ Moderator")
        elif obj.is_moderator_validated is False:
            indicators.append("✗ Moderator")

        workflow_info = " | ".join(indicators) if indicators else ""

        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span><br><small>{}</small>',
            color,
            obj.get_status_display(),
            workflow_info,
        )

    workflow_status.short_description = "Workflow Status"

    def days_since_creation(self, obj):
        """Display days since post creation"""
        delta = timezone.now() - obj.created_at
        days = delta.days

        color = "#28a745" if days <= 3 else "#ffc107" if days <= 7 else "#dc3545"

        return format_html(
            '<span style="color: {}; font-weight: bold;">{} days</span>', color, days
        )

    days_since_creation.short_description = "Age"

    def workflow_timeline(self, obj):
        """Display workflow timeline with timestamps"""
        timeline = []

        timeline.append(f"Created: {obj.created_at.strftime('%Y-%m-%d %H:%M')}")

        if obj.client_approved_at:
            timeline.append(
                f"✓ Client Approved: {obj.client_approved_at.strftime('%Y-%m-%d %H:%M')}"
            )
        elif obj.client_rejected_at:
            timeline.append(
                f"✗ Client Rejected: {obj.client_rejected_at.strftime('%Y-%m-%d %H:%M')}"
            )

        if obj.moderator_validated_at:
            timeline.append(
                f"✓ Moderator Validated: {obj.moderator_validated_at.strftime('%Y-%m-%d %H:%M')}"
            )
        elif obj.moderator_rejected_at:
            timeline.append(
                f"✗ Moderator Rejected: {obj.moderator_rejected_at.strftime('%Y-%m-%d %H:%M')}"
            )

        if obj.published_at:
            timeline.append(
                f"📢 Published: {obj.published_at.strftime('%Y-%m-%d %H:%M')}"
            )

        timeline.append(f"Last Updated: {obj.updated_at.strftime('%Y-%m-%d %H:%M')}")

        return format_html("<br>".join(timeline))

    workflow_timeline.short_description = "Workflow Timeline"

    def change_history(self, obj):
        """Display change statistics"""
        changes = []

        # Calculate time between key events
        if obj.client_approved_at and obj.created_at:
            client_response_time = obj.client_approved_at - obj.created_at
            changes.append(f"Client response time: {client_response_time.days} days")

        if obj.moderator_validated_at and obj.client_approved_at:
            moderator_response_time = (
                obj.moderator_validated_at - obj.client_approved_at
            )
            changes.append(
                f"Moderator response time: {moderator_response_time.days} days"
            )

        if obj.published_at and obj.created_at:
            total_time = obj.published_at - obj.created_at
            changes.append(f"Total workflow time: {total_time.days} days")

        # Track revisions based on last_edited_by changes
        if obj.last_edited_by and obj.last_edited_by != obj.creator:
            changes.append(f"Last edited by: {obj.last_edited_by.email}")

        return (
            format_html("<br>".join(changes)) if changes else "No significant changes"
        )

    change_history.short_description = "Change Statistics"

    def time_in_workflow(self, obj):
        """Calculate time spent in workflow"""
        if obj.status == "published" and obj.published_at:
            total_time = obj.published_at - obj.created_at
        else:
            total_time = timezone.now() - obj.created_at

        days = total_time.days
        hours = total_time.seconds // 3600

        if days > 0:
            return f"{days} days, {hours} hours"
        else:
            return f"{hours} hours"

    time_in_workflow.short_description = "Time in Workflow"

    def total_revisions(self, obj):
        """Estimate total revisions (simplified)"""
        revisions = 0

        # Count major workflow events as revisions
        if obj.client_rejected_at:
            revisions += 1
        if obj.moderator_rejected_at:
            revisions += 1
        if obj.feedback and obj.feedback.strip():
            revisions += 1

        return f"{revisions} revisions"

    total_revisions.short_description = "Estimated Revisions"

    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related(
            "creator", "client", "last_edited_by", "feedback_by", "platform_page"
        )

    # Custom actions for bulk operations
    actions = ["mark_as_approved", "mark_as_rejected", "reset_workflow"]

    def mark_as_approved(self, request, queryset):
        """Bulk approve posts"""
        updated = 0
        for post in queryset:
            post.set_client_approved(request.user)
            post.save()
            updated += 1
        self.message_user(request, f"{updated} posts marked as approved.")

    mark_as_approved.short_description = "Mark selected posts as client approved"

    def mark_as_rejected(self, request, queryset):
        """Bulk reject posts"""
        updated = 0
        for post in queryset:
            post.set_client_rejected(request.user)
            post.save()
            updated += 1
        self.message_user(request, f"{updated} posts marked as rejected.")

    mark_as_rejected.short_description = "Mark selected posts as rejected"

    def reset_workflow(self, request, queryset):
        """Reset workflow for posts"""
        updated = 0
        for post in queryset:
            post.set_resubmitted(request.user)
            post.save()
            updated += 1
        self.message_user(request, f"{updated} posts workflow reset.")

    reset_workflow.short_description = "Reset workflow for selected posts"


# Register the models
admin.site.register(Post, PostAdmin)
admin.site.register(Media, MediaAdmin)

# Add the stats URL to the admin site
from django.contrib.admin import AdminSite

# Extend the admin site to include custom URLs
original_get_urls = admin.site.get_urls


def get_urls_with_stats():
    from django.urls import path

    urls = original_get_urls()
    custom_urls = [
        path(
            "content/stats/",
            PostAdmin(Post, admin.site).content_stats_view,
            name="content_stats",
        ),
    ]
    return custom_urls + urls


admin.site.get_urls = get_urls_with_stats
