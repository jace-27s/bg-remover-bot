import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ["BOT_TOKEN"]  # required — get it from @BotFather

# How many background-removal jobs can run at the same time.
# Each job is memory-heavy (the model + a full-resolution image in RAM), so on a
# 1GB host (Railway trial/Hobby) keep this at 1 to avoid out-of-memory crashes.
# Raise it only if you've upgraded to a plan with more RAM.
MAX_CONCURRENT_JOBS = int(os.getenv("MAX_CONCURRENT_JOBS", "1"))

# Reject uploads larger than this to keep processing time and memory usage predictable.
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "15"))

# Images larger than this (on the longest edge) get downscaled before background
# removal. Mainly keeps decode/encode memory and processing time bounded.
MAX_IMAGE_DIMENSION = int(os.getenv("MAX_IMAGE_DIMENSION", "1600"))

# Which rembg model to use. This is the main lever for memory usage:
#   - "u2net"              ~400-600MB peak RAM, good general quality
#   - "silueta"             similar to u2net, smaller model file, slightly faster
#   - "isnet-general-use"  ~1.5-2GB peak RAM, best edge/hair detail (DEFAULT — needs a 2GB+ RAM host)
# If you're on a 1GB RAM host (e.g. Railway trial), switch this back to "u2net"
# to avoid out-of-memory crashes.
REMBG_MODEL = os.getenv("REMBG_MODEL", "isnet-general-use")

# Minimum seconds between requests from the same user (basic anti-spam / anti-abuse).
RATE_LIMIT_SECONDS = int(os.getenv("RATE_LIMIT_SECONDS", "3"))
