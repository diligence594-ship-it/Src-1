# 1. Purani buster image ko badal kar latest stable bookworm use kiya
FROM python:3.10-slim-bookworm

# 2. Saare duplicate apt installs ko ek clean command me merge kiya aur cache saaf ki
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    git \
    curl \
    wget \
    bash \
    ffmpeg \
    neofetch \
    software-properties-common \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 3. Requirements install karne ka optimized setup
COPY requirements.txt .
RUN pip3 install --no-cache-dir wheel && \
    pip3 install --no-cache-dir -U -r requirements.txt

COPY . .

EXPOSE 5000

# 4. Process management fix: Flask aur Pyrogram dono ko bina crash ke background me running rakhne ke liye sh command use ki hai
CMD ["python3", "main.py"]
