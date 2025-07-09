FROM royyana/progjar-jupyter:latest

RUN apt-get update && apt-get install -y \
    libsdl2-2.0-0 \
    libsdl2-image-2.0-0 \
    libsdl2-mixer-2.0-0 \
    libsdl2-ttf-2.0-0 \
    libportmidi0 \
    libfreetype6 \
    python3-pip

# Install Pygame
RUN pip install pygame
RUN pip install requests
