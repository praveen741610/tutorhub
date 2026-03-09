PROGRAM_CATALOG = [
    {
        "slug": "academic-excellence",
        "name": "Academic Excellence",
        "tracks": ["Math", "Science", "English", "Social Studies", "Hindi (optional)"],
        "grades": "1-10",
        "session_format": "1:1 or small group (2-4)",
        "starting_monthly_usd": 179,
    },
    {
        "slug": "chess",
        "name": "Chess",
        "tracks": ["Beginner to Intermediate", "Logical Reasoning"],
        "grades": "1-10",
        "session_format": "Small group (3-5)",
        "starting_monthly_usd": 99,
    },
    {
        "slug": "creative-arts",
        "name": "Creative Arts",
        "tracks": ["Drawing", "Painting", "Indian Art Forms"],
        "grades": "1-8",
        "session_format": "Small group (3-5)",
        "starting_monthly_usd": 109,
    },
    {
        "slug": "music-academy",
        "name": "Music Academy",
        "tracks": ["Carnatic / Hindustani", "Keyboard", "Vocal"],
        "grades": "1-10",
        "session_format": "1:1 or small group",
        "starting_monthly_usd": 139,
    },
    {
        "slug": "inclusive-learning",
        "name": "Inclusive Learning",
        "tracks": ["Structured Academic Support", "Behavioral Learning Support"],
        "grades": "1-8",
        "session_format": "1:1 or small group (2-3)",
        "starting_monthly_usd": 199,
    },
]

PROGRAM_BY_SLUG = {entry["slug"]: entry for entry in PROGRAM_CATALOG}

PLAN_TO_MONTHS = {
    "monthly": 1,
    "quarterly": 3,
    "annual": 12,
}

PLAN_DISCOUNT_PERCENT = {
    "monthly": 0,
    "quarterly": 8,
    "annual": 18,
}

BUNDLE_DISCOUNT_PERCENT = 10

BOOKING_KIND_DURATION_MINUTES = {
    "trial": 45,
    "consultation": 30,
}
