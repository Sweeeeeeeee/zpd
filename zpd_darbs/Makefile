# ZPD darba būvēšana. Prasības: TeX Live (pdflatex, latexmk), .venv-newclid ar matplotlib.
PY ?= ../.venv-newclid/bin/python
LATEXMK = latexmk -pdf -interaction=nonstopmode -halt-on-error

.PHONY: all figures template preliminary clean
all: figures template preliminary

figures:            ## attēli un tabulas no ../results/
	$(PY) scripts/make_figures.py

template:           ## tukšā veidne
	cd template && $(LATEXMK) template.tex

preliminary: figures ## priekšvariants ar projekta saturu
	cd preliminary && $(LATEXMK) template_preliminary.tex

clean:
	cd template && latexmk -c template.tex
	cd preliminary && latexmk -c template_preliminary.tex
