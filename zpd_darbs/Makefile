# ZPD darba būvēšana. Prasības: TeX Live (pdflatex, latexmk), .venv-newclid ar matplotlib.
PY ?= ../.venv-newclid/bin/python
LATEXMK = latexmk -pdf -interaction=nonstopmode -halt-on-error

.PHONY: all figures publication template preliminary presentation clean
all: figures template preliminary

figures:            ## attēli un tabulas no ../results/
	$(PY) scripts/make_figures.py

template:           ## tukšā veidne
	cd template && $(LATEXMK) template.tex

publication:          ## HTML rezultāti un CPU pārbaudes teksts no saglabātajiem datiem
	PYTHONPATH=.. $(PY) -m bench.publish

preliminary: figures publication ## priekšvariants ar projekta saturu
	cd preliminary && $(LATEXMK) template_preliminary.tex

presentation: publication  ## 8 slaidi no saglabātajiem pētījuma rezultātiem
	$(PY) scripts/presentation_data.py
	cd prezentacija && SOURCE_DATE_EPOCH=1795305600 FORCE_SOURCE_DATE=1 latexmk -lualatex -interaction=nonstopmode -halt-on-error prezentacija.tex

clean:
	cd prezentacija && latexmk -c prezentacija.tex
	cd template && latexmk -c template.tex
	cd preliminary && latexmk -c template_preliminary.tex
