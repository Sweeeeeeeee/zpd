# ZPD darbs

Everything for the written ZPD paper: the official guidelines, a LaTeX
template that follows them, a preliminary version filled with this project's
content, and the scripts that build its figures and tables from `results/`.

| path | what |
|---|---|
| `vadlinijas/vadlinijas_zpd_2026_2027.pdf` | official VIAA guidelines (2026), the source of every formatting rule |
| `template/zpd.cls` | document class: A4, 2.5 cm margins, Times 12 pt, single spacing, 16/14 pt bold headings, indented justified paragraphs, page numbers bottom centre from the introduction |
| `template/template.tex` | empty template in the structure of guidelines section 2 (title page, both abstracts, contents, introduction, chapters, conclusions, sources, appendices) |
| `template/logo.png` | logo strip from the guidelines' cover (ESF+, Latvija 2027, VIAA) |
| `preliminary/template_preliminary.tex` | preliminary paper: the template filled with the project's aim, tasks, method and current results |
| `scripts/make_figures.py` | builds `figures/*.pdf` and `tables/*.tex` from `results/` |
| `figures/`, `tables/` | generated; rebuild with `make figures` |

## Build

```bash
cd zpd_darbs
make            # figures + template.pdf + template_preliminary.pdf
make preliminary
```

Needs TeX Live (`pdflatex`, `latexmk`, `texlive-lang-european` for Latvian)
and `../.venv-newclid` with matplotlib. With XeLaTeX the class uses Times New
Roman when the font is installed.

## Red labels

`\zpdlabel{...}` prints a small red label saying what each part is (title,
supervisor, aim, hypothesis, ...). `\zpdnote{...}` is a red note on what a
chapter must contain. `\aizpildit{...}` marks red text that still has to be
filled in: the school, names, city, and results that need the scan (tasks 7 and 9–10).
For the version to submit, switch them all off with:

```latex
\documentclass[nolabels]{../template/zpd}   % nologo hides the logo
```

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

The page limit is 16 pages including the title page; the preliminary version
has 11.
