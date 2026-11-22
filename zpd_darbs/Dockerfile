FROM python:3.13-slim
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends latexmk texlive-latex-extra texlive-lang-european texlive-fonts-recommended lmodern && rm -rf /var/lib/apt/lists/*
# LuaLaTeX embeds Unicode text for searchable Latvian presentation slides.
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends texlive-luatex fonts-liberation && rm -rf /var/lib/apt/lists/*
