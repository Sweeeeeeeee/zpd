%% zpd.cls -- skolēnu zinātniskās pētniecības darba (ZPD) klase
%% Noformējums pēc VISC/VIAA "Vadlīnijas skolēnu zinātniskās pētniecības darbu
%% izstrādei un vērtēšanai" (2026), 3. nodaļa un 3.-5. pielikums:
%%   A4, visas malas 2,5 cm, rindstarpa 1,0, Times New Roman 12 pt,
%%   virsraksti 16/14 pt treknrakstā, melns teksts, rindkopas ar atkāpi,
%%   abpusēji izlīdzināts teksts (izņemot tabulas un avotu sarakstu),
%%   lappušu numurs apakšā pa vidu, redzams no Ievada lappuses.
%%
%% Klases opcijas:
%%   labels   / nolabels  -- rādīt / slēpt sarkanās piezīmes \zpdlabel{...} (noklusēti: labels)
%%   logo     / nologo    -- rādīt / slēpt skolas logotipu titullapā (noklusēti: logo; fails \logotips{...})
%%   draft                -- nodod tālāk article klasei
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{zpd}[2026/11/05 ZPD darba klase pec 2026. gada vadlinijam]

\newif\ifzpd@labels \zpd@labelstrue
\newif\ifzpd@logo   \zpd@logotrue
\DeclareOption{labels}{\zpd@labelstrue}
\DeclareOption{nolabels}{\zpd@labelsfalse}
\DeclareOption{logo}{\zpd@logotrue}
\DeclareOption{nologo}{\zpd@logofalse}
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{article}}
\ProcessOptions\relax
\LoadClass[a4paper,12pt]{article}

%% ---------------------------------------------------------------- lapa
\RequirePackage[a4paper,margin=2.5cm,includefoot=false,footskip=1.2cm]{geometry}
\RequirePackage{iftex}

%% ---------------------------------------------------------------- fonts un valoda
\ifPDFTeX
  \RequirePackage[T1]{fontenc}
  \RequirePackage[utf8]{inputenc}
  \IfFileExists{newtxtext.sty}{%
    \RequirePackage{newtxtext}\RequirePackage{newtxmath}}{%
    \IfFileExists{tgtermes.sty}{\RequirePackage{tgtermes}}{\RequirePackage{mathptmx}}}
\else
  \RequirePackage{fontspec}
  \IfFontExistsTF{Times New Roman}
    {\setmainfont{Times New Roman}}
    {\IfFontExistsTF{TeX Gyre Termes}{\setmainfont{TeX Gyre Termes}}{\setmainfont{Liberation Serif}}}
\fi
\RequirePackage[latvian]{babel}
\ifPDFTeX\RequirePackage[scaled=0.92]{helvet}\fi
\RequirePackage[expansion=false]{microtype}

%% ---------------------------------------------------------------- pamatpaketes
\RequirePackage{xcolor}
\RequirePackage{graphicx}
\RequirePackage{booktabs}
\RequirePackage{array}
\RequirePackage{tabularx}
\RequirePackage{amsmath,amssymb}
\RequirePackage{enumitem}
\RequirePackage{caption}
\RequirePackage{float}
% titlesec 2.13 (TeX Live 2019, e.g. the Ubuntu 20.04 Codespace image) reads
% \c@chapter even in article; a zero counter keeps it happy. No effect on newer TeX Live.
\ifdefined\c@chapter\else\newcount\c@chapter\fi
\RequirePackage{titlesec}
\RequirePackage{titletoc}
\AtBeginDocument{\renewcommand{\theHsection}{\arabic{section}}}  % article: hyperref enkuri bez nodaļu skaitītāja
\RequirePackage[hidelinks]{hyperref}
\RequirePackage{url}

%% ---------------------------------------------------------------- rindstarpa un rindkopas
\linespread{1.0}
\setlength{\parindent}{1.25cm}
\setlength{\parskip}{0pt}
\setlength{\emergencystretch}{2em}
\color{black}

%% ---------------------------------------------------------------- virsraksti
%% Nodaļa (\section): 16 pt, treknraksts, centrēts.  Apakšnodaļa: 14 pt, treknraksts.
\titleformat{\section}{\centering\fontsize{16}{19}\selectfont\bfseries}{\thesection}{0.5em}{}
\titleformat{\subsection}{\fontsize{14}{17}\selectfont\bfseries}{\thesubsection}{0.5em}{}
\titleformat{\subsubsection}{\normalsize\bfseries}{\thesubsubsection}{0.5em}{}
\titlespacing*{\section}{0pt}{0pt}{18pt}
\titlespacing*{\subsection}{0pt}{12pt}{6pt}
\titlespacing*{\subsubsection}{0pt}{10pt}{4pt}
\newcommand{\sectionbreak}{\clearpage}  % katra nodaļa sākas jaunā lappusē

%% Nenumurēta daļa satura rādītājā (Ievads, Secinājumi, Avoti ...)
\newcommand{\nenumuretanodala}[1]{%
  \clearpage\phantomsection
  \section*{#1}\addcontentsline{toc}{section}{#1}}

%% ---------------------------------------------------------------- satura rādītājs
\addto\captionslatvian{\renewcommand{\contentsname}{Saturs}}
\titlecontents{section}[0pt]{\addvspace{3pt}}
  {\contentslabel{1.5em}}{}{\titlerule*[0.6pc]{.}\contentspage}
\titlecontents{subsection}[3em]{}
  {\contentslabel{2.2em}}{}{\titlerule*[0.6pc]{.}\contentspage}
\newcommand{\saturs}{%
  \clearpage
  \section*{\contentsname}
  \@starttoc{toc}
  \clearpage}

%% ---------------------------------------------------------------- attēli un tabulas
%% Kā RTU IZV paraugā: numurēti pa nodaļām, slīprakstā, numurs treknrakstā:
%% "4.1. attēls Nosaukums" zem attēla; "4.1. tabula Nosaukums" virs tabulas.
\addto\captionslatvian{\renewcommand{\figurename}{attēls}\renewcommand{\tablename}{tabula}}
\counterwithin{figure}{section}
\counterwithin{table}{section}
\AtBeginDocument{\renewcommand{\thefigure}{\arabic{section}.\arabic{figure}.}\renewcommand{\thetable}{\arabic{section}.\arabic{table}.}}
\DeclareCaptionLabelFormat{lvnum}{#2~#1}
\captionsetup{labelformat=lvnum,labelsep=space,font={small,it},labelfont={bf,it},justification=centering}
\captionsetup[table]{position=top,skip=4pt}
\captionsetup[figure]{skip=4pt}
\renewcommand{\arraystretch}{1.15}

%% ---------------------------------------------------------------- saraksti un secinājumi
\setlist{itemsep=0pt,topsep=3pt,parsep=0pt}
\newenvironment{secinajumi}{\begin{enumerate}[label=\arabic*.,leftmargin=*,itemsep=3pt]}{\end{enumerate}}

%% ---------------------------------------------------------------- sarkanās piezīmes
%% \zpdlabel{Darba nosaukums} -- sarkana piezīme, kas paskaidro, kas ir blakus esošais teksts.
%% Ar klases opciju "nolabels" visas piezīmes pazūd, un darbs ir gatavs iesniegšanai.
\definecolor{zpdlabel}{RGB}{200,16,16}
\ifzpd@labels
  \newcommand{\zpdlabel}[1]{{\color{zpdlabel}\sffamily\footnotesize\bfseries[#1]}\hspace{0.4em plus 1em}\allowbreak}
  \newcommand{\zpdnote}[1]{\par{\color{zpdlabel}\sffamily\footnotesize #1}\par}
\else
  \newcommand{\zpdlabel}[1]{}
  \newcommand{\zpdnote}[1]{}
\fi
%% Vieta, ko vēl jāaizpilda: sarkans, iekavās.
\newcommand{\aizpildit}[1]{{\color{zpdlabel}[#1]}}

%% ---------------------------------------------------------------- titullapa (3. pielikums)
\newcommand{\skola}[1]{\def\zpd@skola{#1}}
\newcommand{\nosaukums}[1]{\def\zpd@nosaukums{#1}}
\newcommand{\nozaru}[1]{\def\zpd@nozaru{#1}}
\newcommand{\autors}[2][Darba autors]{\def\zpd@autorsl{#1}\def\zpd@autors{#2}}
\newcommand{\vaditajs}[2][Darba vadītājs]{\def\zpd@vaditajsl{#1}\def\zpd@vaditajs{#2}}
\newcommand{\konsultants}[2][Darba konsultants]{\def\zpd@konsultantsl{#1}\def\zpd@konsultants{#2}}
\newcommand{\pilseta}[1]{\def\zpd@pilseta{#1}}
\newcommand{\gads}[1]{\def\zpd@gads{#1}}
\newcommand{\logotips}[1]{\def\zpd@logofile{#1}}
\skola{\aizpildit{Izglītības iestādes nosaukums}}
\nosaukums{\aizpildit{Darba nosaukums}}
\nozaru{\aizpildit{zinātnes nozaru grupas / nozares nosaukums} nozarē}
\autors{\aizpildit{Vārds Uzvārds}}
\vaditajs{\aizpildit{Vārds Uzvārds}}
\let\zpd@konsultants\relax
\pilseta{\aizpildit{Pilsēta}}
\gads{\the\year}
\logotips{logo_rtu_izv.png}

%% Izkārtojums kā RTU IZV paraugā (zpd_darbs/vadlinijas/example_rtu_izv.pdf) un vadlīniju 3. pielikumā.
\newcommand{\titullapa}{%
  \begin{titlepage}
    \centering
    \ifzpd@logo
      \IfFileExists{\zpd@logofile}{\vspace*{1.2cm}\includegraphics[height=4.2cm]{\zpd@logofile}\par\vspace{0.8cm}}{}
    \fi
    \zpdlabel{Izglītības iestāde}\zpd@skola\par
    \vspace{2.6cm}
    \zpdlabel{Darba nosaukums}\par
    {\fontsize{16}{19}\selectfont\bfseries\zpd@nosaukums\par}
    \vspace{1.0cm}
    \zpdlabel{Zinātnes nozaru grupa / nozare}Zinātniskās pētniecības darbs \zpd@nozaru\par
    \vspace{1.0cm}
    \begin{flushright}
      \textbf{\zpd@autorsl:}\\ \zpd@autors\par\vspace{0.5cm}
      \textbf{\zpd@vaditajsl:}\\ \zpd@vaditajs\par
      \ifx\zpd@konsultants\relax\else\vspace{0.5cm}\textbf{\zpd@konsultantsl:}\\ \zpd@konsultants\par\fi
    \end{flushright}
    \vfill
    \zpdlabel{Pilsēta un gads}\zpd@pilseta{} \zpd@gads\par
  \end{titlepage}
  \setcounter{page}{2}}

%% ---------------------------------------------------------------- anotācijas
%% Abas anotācijas vienā lapā aiz titullapas; atslēgvārdi -- ne vairāk kā pieci.
\newcommand{\anotacijulapa}{\clearpage\thispagestyle{empty}}
\newenvironment{anotacija}[1]{%
  \begin{center}\fontsize{14}{17}\selectfont\bfseries #1\end{center}\vspace{-4pt}}{\par\vspace{14pt}}
\newcommand{\atslegvardi}[2][Atslēgvārdi]{\par\noindent\textbf{#1:} #2\par}

%% ---------------------------------------------------------------- lappušu numerācija
%% Titullapa, anotācijas un saturs tiek skaitīti, bet numurs redzams no Ievada.
\pagestyle{empty}
\newcommand{\pamatteksts}{\clearpage\pagestyle{plain}}
\renewcommand{\ps@plain}{\renewcommand{\@oddhead}{}\renewcommand{\@evenhead}{}%
  \renewcommand{\@oddfoot}{\hfil\normalsize\thepage\hfil}\renewcommand{\@evenfoot}{\@oddfoot}}

%% ---------------------------------------------------------------- avotu saraksts (5. pielikums)
%% Alfabētiski, bez numuriem, ar karājošo atkāpi, nav abpusēji izlīdzināts.
\newenvironment{avoti}{%
  \nenumuretanodala{Izmantotās literatūras un informācijas avotu saraksts}
  \begin{list}{}{\setlength{\leftmargin}{1.25cm}\setlength{\itemindent}{-1.25cm}
     \setlength{\itemsep}{4pt}\setlength{\parsep}{0pt}}\raggedright}
  {\end{list}}
\newcommand{\avots}{\item}
%% Atsauce tekstā (4. pielikums, 1. variants): \atsauce{Trinh u.c., 2024, 478} -> (Trinh u.c., 2024, 478)
\newcommand{\atsauce}[1]{(#1)}

%% ---------------------------------------------------------------- pielikumi
\newcounter{pielikums}
\newcommand{\pielikums}[1]{%
  \clearpage\refstepcounter{pielikums}\phantomsection
  \addcontentsline{toc}{section}{\thepielikums.~pielikums. #1}
  \begin{flushright}\thepielikums.~pielikums\\\relax #1\end{flushright}\vspace{6pt}}

\endinput
