from django.core.management.base import BaseCommand
from apps.ai_integration.models import HashtagPerformance, OptimalPostingTime
import random
from faker import Faker

fake = Faker()

HASHTAG_DATA = {
    "fitness": [
        "fitness",
        "gym",
        "workout",
        "fitnessmotivation",
        "bodybuilding",
        "fitfam",
        "fitlife",
        "gymmotivation",
        "healthylifestyle",
        "cardio",
        "strengthtraining",
        "fitnessgirl",
        "fitnessmodel",
        "instafit",
        "trainhard",
        "fitnesscommunity",
        "workoutmotivation",
        "fitnessguru",
        "gains",
        "shred",
    ],
    "fashion": [
        "fashion",
        "style",
        "fashionblogger",
        "ootd",
        "fashionista",
        "fashiongirl",
        "fashiontrend",
        "fashionable",
        "fashionlover",
        "streetwear",
        "fashiondesigner",
        "fashionshow",
        "couture",
        "fashionweek",
        "instastyle",
        "fashiondaily",
        "fashionforward",
        "fashionkiller",
        "fashionaddict",
        "lookbook",
    ],
    "tech": [
        "tech",
        "technology",
        "programming",
        "coding",
        "developer",
        "startup",
        "innovation",
        "ai",
        "blockchain",
        "software",
        "webdevelopment",
        "appdevelopment",
        "python",
        "javascript",
        "react",
        "techstartup",
        "techblog",
        "techtips",
        "coding",
        "developer",
    ],
    "food": [
        "food",
        "foodblogger",
        "foodphotography",
        "foodstagram",
        "foodie",
        "instafood",
        "foodlover",
        "foodblog",
        "foodiesofinstagram",
        "cooking",
        "recipe",
        "yummy",
        "foodgasm",
        "homemade",
        "delicious",
        "restaurantfood",
        "streetfood",
        "dessert",
        "lunch",
        "dinner",
    ],
    "travel": [
        "travel",
        "travelblogger",
        "travelgram",
        "wanderlust",
        "instatravel",
        "traveldiaries",
        "beautifuldestinations",
        "adventure",
        "backpacking",
        "roadtrip",
        "explore",
        "travelphotography",
        "travelgirl",
        "travelboy",
        "bucket list",
        "travelinspo",
        "vacation",
        "holiday",
        "destination",
        "travelmemories",
    ],
    "lifestyle": [
        "lifestyle",
        "lifestyleblogger",
        "dailylife",
        "instagood",
        "motivation",
        "wellness",
        "selfcare",
        "happiness",
        "mindfulness",
        "personaldev",
        "goals",
        "dreams",
        "inspire",
        "blessed",
        "grateful",
        "dayinmylife",
        "morningroutine",
        "eveningroutine",
        "lifestyle",
        "lifeupdate",
    ],
    "business": [
        "business",
        "entrepreneur",
        "startup",
        "businessowner",
        "success",
        "marketing",
        "sales",
        "leadership",
        "mindset",
        "grind",
        "hustle",
        "motivated",
        "buildit",
        "businesstips",
        "businessclass",
        "networking",
        "corporate",
        "mentor",
        "growth",
        "scaling",
    ],
    "marketing": [
        "marketing",
        "socialmediamarketing",
        "marketingtips",
        "contentmarketing",
        "digitalmarketing",
        "seo",
        "marketingstrategy",
        "branding",
        "marketingagency",
        "marketingguru",
        "leadsgeneration",
        "conversion",
        "engagement",
        "marketinganalysis",
        "marketingautomation",
        "influencermarketing",
        "contentcreator",
        "copywriting",
        "marketinglife",
        "growthmarketing",
    ],
}


class Command(BaseCommand):
    help = "Generate synthetic hashtag performance data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--industry",
            type=str,
            default="all",
            help="Industry to generate (all, fitness, fashion, tech, etc.)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing hashtags before generating",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            HashtagPerformance.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Cleared existing hashtags"))

        industries = (
            [options["industry"]]
            if options["industry"] != "all"
            else list(HASHTAG_DATA.keys())
        )

        for industry in industries:
            hashtags = HASHTAG_DATA.get(industry, [])
            platform_choices = ["instagram", "facebook", "linkedin"]

            for hashtag in hashtags:
                for platform in platform_choices:
                    # Skip linkedin for non-business hashtags
                    if platform == "linkedin" and industry not in [
                        "business",
                        "tech",
                        "marketing",
                    ]:
                        continue

                    # Generate synthetic engagement
                    engagement = random.uniform(0.5, 8.5)
                    usage = random.randint(50, 500)
                    reach = random.randint(1000, 50000)
                    trending = random.random() < 0.2  # 20% are trending

                    HashtagPerformance.objects.update_or_create(
                        hashtag=hashtag,
                        platform=platform,
                        defaults={
                            "industry": industry,
                            "avg_engagement_rate": engagement,
                            "usage_frequency": usage,
                            "reach_estimate": reach,
                            "trending": trending,
                        },
                    )

            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Generated {len(hashtags)} hashtags for {industry}"
                )
            )

        # Generate optimal posting times
        self._generate_posting_times()

    def _generate_posting_times(self):
        OptimalPostingTime.objects.all().delete()

        platforms = ["instagram", "facebook", "linkedin"]
        # Best times typically 6-10am and 7-11pm
        best_hours = {
            "instagram": [6, 7, 8, 9, 19, 20, 21, 22],
            "facebook": [10, 11, 18, 19, 20],
            "linkedin": [7, 8, 9, 12, 17, 18],
        }

        for platform in platforms:
            for day in range(7):  # 0-6
                for hour in range(24):
                    # Higher score for optimal hours
                    if hour in best_hours.get(platform, []):
                        score = random.uniform(70, 90)
                    else:
                        score = random.uniform(30, 60)

                    OptimalPostingTime.objects.create(
                        platform=platform,
                        day_of_week=day,
                        hour=hour,
                        engagement_score=score,
                    )

        self.stdout.write(self.style.SUCCESS("✅ Generated optimal posting times"))
