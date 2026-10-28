import os
from dotenv import load_dotenv

load_dotenv()

# =========================
# KYŌKA CONFIGURATION
# =========================

# Discord
TOKEN = os.getenv("DISCORD_TOKEN")

# Command prefix
PREFIX = "k!"

# Creator / Owner
OWNER_ID = 1505515188991033409

# Database
DATABASE_PATH = os.getenv("DATABASE_PATH", "database/kyoka.db")

# Bot settings
BOT_NAME = "KYŌKA"
VERSION = "1.0.0"

# Environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")

# Premium
PREMIUM_ENABLED = True

# AI
AI_ENABLED = True

# Music
MUSIC_ENABLED = True


def is_owner(user_id: int) -> bool:
    """Check whether a Discord user is the KYŌKA creator."""
    return user_id == OWNER_ID


if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN is missing. Add your bot token to the .env file."
    )
