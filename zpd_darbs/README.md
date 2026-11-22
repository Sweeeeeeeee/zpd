# ZPD darbs

Everything for the written ZPD paper: the official guidelines, a LaTeX
template that follows them, a preliminary version filled with this project's
content, and the scripts that build its figures and tables from `results/`.

| path | what |
|---|---|
| `vadlinijas/vadlinijas_zpd_2026_2027.pdf` | official VIAA guidelines (2026), the source of every formatting rule |
| `vadlinijas/example_rtu_izv.pdf` | example RTU IZV paper, the source of the look (logo, title page, captions) |
| `template/zpd.cls` | document class: A4, 2.5 cm margins, Times 12 pt, single spacing, 16/14 pt bold headings, indented justified paragraphs, page numbers bottom centre from the introduction |
| `template/template.tex` | empty template in the structure of guidelines section 2 (title page, both abstracts, contents, introduction, chapters, conclusions, sources, appendices) |
| `template/logo_rtu_izv.png` | RTU Inženierzinātņu vidusskola logo, taken from `zpd_darbs/vadlinijas/example_rtu_izv.pdf` (the reference for the look: title page, captions); change with `\logotips{...}` |
| `preliminary/template_preliminary.tex` | preliminary paper: the template filled with the project's aim, tasks, method and current results (revised 2026-11-22 with a local CPU replication) |
| `scripts/make_figures.py` | builds `figures/*.pdf` and `tables/*.tex` from `results/` |
| [prezentacija/](prezentacija/) | eight-slide Latvian talk, timed notes, editable diagrams and generated data |
| `figures/`, `tables/` | generated; rebuild with `make figures` |

## Build

```bash
cd zpd_darbs
make            # figures + template.pdf + template_preliminary.pdf
make preliminary
make presentation  # LuaLaTeX and Liberation Sans
```

Needs TeX Live (`pdflatex`, `latexmk`, `texlive-lang-european` for Latvian)
and `../.venv-newclid` with matplotlib. With XeLaTeX the class uses Times New
Roman when the font is installed.

To use an activated local Python environment, pass `make PY="$(command -v python)" preliminary`. For a host without TeX, rebuild the tables and HTML with that interpreter, then compile the existing TeX source in a container. From this directory:

```sh
make PY="$(command -v python)" figures publication
docker build -t zpd-paper-local - < Dockerfile
docker run --rm --network none --user "$(id -u):$(id -g)" -e HOME=/tmp \
  -v "$PWD:/paper" -w /paper/preliminary zpd-paper-local \
  latexmk -pdf -interaction=nonstopmode -halt-on-error template_preliminary.tex
```

To build the presentation with the same image, run these commands from `zpd_darbs/` with the project environment activated:

```sh
make PY="$(command -v python)" publication
python scripts/presentation_data.py
docker run --rm --network none --user "$(id -u):$(id -g)" -e HOME=/tmp \
  -e SOURCE_DATE_EPOCH=1795305600 -e FORCE_SOURCE_DATE=1 \
  -v "$PWD:/paper" -w /paper/prezentacija zpd-paper-local \
  latexmk -lualatex -interaction=nonstopmode -halt-on-error prezentacija.tex
```

## Public research draft

The paper uses the class’s `nolabels` option to hide editorial annotations. Unknown author and supervisor names are explicitly left unspecified for this public draft. The blank template retains its teaching annotations. The local replication paragraph comes from `tables/local_eval.tex`; regenerate it with `python -m bench.publish` at the repository root before rebuilding the PDF.

## What the class implements

| guideline | class |
|---|---|
| title page (appendix 3) | `\titullapa` with `\skola`, `\nosaukums`, `\nozaru`, `\autors`, `\vaditajs`, `\konsultants`, `\pilseta`, `\gads` |
| both abstracts on one page, at most 5 keywords | `\anotacijulapa`, `anotacija` environment, `\atslegvardi` |
| unnumbered introduction, conclusions and sources, all in the contents | `\nenumuretanodala{...}`, `\saturs` |
| page numbers visible from the introduction | `\pamatteksts` |
| figure captions below, table titles above, numbered | `1. attēls.` / `1. tabula.` via `caption` |
| conclusions as numbered theses | `secinajumi` environment |
| in-text references, variant 1 (appendix 4) | `\atsauce{Trinh u.c., 2024, 478}` → (Trinh u.c., 2024, 478) |
| sources list, alphabetical, not justified (appendix 5) | `avoti` environment with `\avots` |
| appendices numbered, in the contents | `\pielikums{Title}` |
