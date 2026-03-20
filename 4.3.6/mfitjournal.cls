%%  Article document class of the journal KRAUNC.MFIT
%%  for LaTeX2e
%%  mfitart.cls
%%
%%  (c) IKIR FEBRAS, KAMGU by VITUS BERING
%%

%======================================================================

%\endinput
\NeedsTeXFormat{LaTeX2e}
\ProvidesPackage{mfitjournal}[27/12/2009 Perezhogin Andrey,Parovik Roman]
\DeclareOption{12pt}{\relax}
\DeclareOption{twoside}{\relax}
%\DeclareOption*{\PassOptionToClass{\CurrentOption}{journal}}
\ProcessOptions
\PassOptionsToClass{twoside,12pt,journal,a4paper}{journal}	
\LoadClass{journal}
\RequirePackage[utf8]{inputenc}	
\RequirePackage[T2A]{fontenc}	
\RequirePackage{ifthen}	
\RequirePackage[english, russian]{babel}	
%\RequirePackage{amsbib}	
\RequirePackage{footmisc}
\usepackage{fancyhdr}
\RequirePackage{misccorr}
\RequirePackage{mathptmx}
\RequirePackage{textcomp}
%\RequirePackage{pscyr}
\RequirePackage{multirow}
\RequirePackage{wrapfig}
\RequirePackage{epstopdf}
%\RequirePackage{eso-pic}						%russian language
\RequirePackage[top=2.5cm, left=2.5cm, right=2.5cm, bottom=2.7cm]{geometry} %pagesize
%\RequirePackage[pdftex, unicode]{hyperref}					%hyperref for pdf
\RequirePackage{cmap}								%search russian in pdf
%\RequirePackage{type1ec}							%true type fonts cm
\RequirePackage{graphicx}							%for graphic \includegraphics
\RequirePackage{caption}                            %for cation separator
\DeclareCaptionLabelSeparator{colon}{.~}					%picture separator -- point
\RequirePackage{indentfirst}							%first abzac
\RequirePackage{amsmath}							%math package
\RequirePackage{amsfonts}							%math fonts
\RequirePackage{rotating}
\RequirePackage{mathtext}
\RequirePackage{amssymb}
%\RequirePackage{setspace}	

%==============================================math symbols
 %%
%% This is file `paper.cls',
%% generated with the docstrip utility.
%%
%% The original source files were:
%%
%% paper.dtx  (with options: `paper')
%% 
%% Copyright (C) 1993, 1998 by wenzel_matiaske@notes.uni-paderborn.de
%% 
%% You are not allowed to distribute this file without the
%% original source paper.dtx. For distribution of the
%% sources see the copyright notice in the file paper.dtx.
%% 

%=======define abstract============================

%define abstract
\renewcommand\abstract{
\small
\quotation
}

%==============================================================
\newcommand{\@maketabcaption}[2]{
\begin{flushright}
\it #1 \\
\end{flushright}
\begin{center}
\vspace{-0.5em} \bf #2 \vspace{-1em}
\end{center}
}
\renewcommand{\table}{
\let\@makecaption\@maketabcaption\@float{table}
} 
%==============define
\newcommand{\SEC}{}
\newcommand{\SECC}[1]{%
   \renewcommand{\SEC}{{\noindent\ignorespaces\normalsize #1}}}
\newcommand{\ESEC}{}
\newcommand{\ESECC}[1]{%
   \renewcommand{\ESEC}{{\noindent\ignorespaces\normalsize #1}}}
%name======================================
\renewcommand{\figureshortname}{\inputencoding{utf8} \small Рис.} 
\renewcommand\tableshortname{\inputencoding{utf8} Таблица} 
\renewcommand\refname{\inputencoding{utf8}Список литературы} 
\renewcommand\indexname{\inputencoding{utf8}Предметный указатель} 
\renewcommand\listfigurename{\inputencoding{utf8}Список рисунков} 
\renewcommand\listtablename{\inputencoding{utf8}Список таблиц} 
%\renewcommand*{\rmdefault}{cmb}
%==============define section====================================
\renewcommand\thesection {\arabic{section}}
\renewcommand\thesubsection {\thesection.\arabic{subsection}}
\renewcommand\thesubsubsection {\thesubsection.\arabic{subsubsection}}
\renewcommand\theparagraph {\thesubsubsection.\arabic{paragraph}}
\renewcommand\thesubparagraph {\theparagraph.\arabic{subparagraph}}
%===================================================================
%\renewcommand{\@oddfoot}{\hfill VESTNIK KRAESC. PHYSICO-MATHEMATICS SCIENCES. %\MFITyear \hspace{0.25em} \No \hspace{0.1em} \MFITnumber .\hfill}
%\renewcommand{\@evenfoot}{\hfill ВЕСТНИК К� АУНЦ. ФИЗИКО-МАТЕМАТИЧЕСКИЕ НАУКИ. \MFITyear \hspace{0.25em} \No \hspace{0.1em} \MFITnumber . \hfill}
%\renewcommand{\@evenhead}{\textnormal \thepage \hfill \it \leftmark}
%\renewcommand{\@oddhead}{\it \rightmark \hfill \textnormal \thepage}
%\renewcommand{\bfdefault}{b}
%==========================engtitle======================================
\newcommand{\engtitle}{}
\newcommand{\thetitle}{}
\renewcommand{\engtitle}[1]{%
   \renewcommand{\thetitle}{\bf\noindent\Large #1}} 
%============================================================
\newcommand{\rustitle}{}
\newcommand{\thertitle}{}
\renewcommand{\rustitle}[1]{%
   \renewcommand{\thertitle}{\bf\noindent\Large #1}} 
%===============================engauthor====================================
\newcommand{\prtitle}{}
\newcommand{\theprtitle}{}
\renewcommand{\prtitle}[1]{%
   \renewcommand{\theprtitle}{\bf\noindent\Large #1}} 
%=========================================================================
\newcommand{\eauthor}{}
\newcommand{\engAuthorInContents}{}
\newcommand{\theauthor}{}
\newcommand{\engauthor}{}
\renewcommand{\engauthor}[1]{%
   \renewcommand{\theauthor}%
   {\bf\Large #1}}  
%===============================definst================================
\def\inst#1{\unskip$^{#1}$}
%========================institute======================================
\newcounter{@inst}
\newdimen\instindent

\def\institute#1{\gdef\@institute{#1}}

\def\institutename{\par
 \begingroup
 \parindent=0pt
 \parskip=0pt
 \setcounter{@inst}{1}%
 \def\and{\par\stepcounter{@inst}%
 \noindent
 \hbox to\instindent{\hss$^{\the@inst}$\enspace}\ignorespaces}%
 \setbox0=\vbox{\@institute}
 \ifnum\c@@inst>9\relax\setbox0=\hbox{$^{88}$\enspace}%
                 \else\setbox0=\hbox{$^{8}$\enspace}\fi
 \instindent=\wd0\relax
 \ifnum\c@@inst=1\relax
 \else
   \setcounter{@inst}{1}%
   \noindent
   \hbox to\instindent{\hss$^{\the@inst}$\enspace}\ignorespaces
 \fi
 \ignorespaces
 \@institute\par
 \endgroup}
%==============================enginstitute===================================
\newcounter{@enginst}
\newdimen\enginstindent

\def\enginstitute#1{\gdef\@enginstitute{#1}}

\def\enginstitutename{\par
 \begingroup
 \parindent=0pt
 \parskip=0pt
 \setcounter{@enginst}{1}%
 \def\and{\par\stepcounter{@enginst}%
 \noindent
 \hbox to\enginstindent{\hss$^{\the@enginst}$\enspace}\ignorespaces}%
 \setbox0=\vbox{\@enginstitute}
 \ifnum\c@@inst>9\relax\setbox0=\hbox{$^{88}$\enspace}%
                 \else\setbox0=\hbox{$^{8}$\enspace}\fi
 \enginstindent=\wd0\relax
 \ifnum\c@@enginst=1\relax
 \else
   \setcounter{@enginst}{1}%
   \noindent
   \hbox to\enginstindent{\hss$^{\the@enginst}$\enspace}\ignorespaces
 \fi
 \ignorespaces
 \@enginstitute\par
 \endgroup}
%============================otherinf=========================================
\newcommand{\theotherinf}{}
\newcommand{\otherinf}[1]{%
           \renewcommand{\theotherinf}{\footnotetext{\it \!\!\!\!\!#1}}}       
%=============================otherenginf===============================================
\newcommand{\theotherenginf}{}
\newcommand{\otherenginf}[1]{%
           \renewcommand{\theotherenginf}{\footnotetext{\it \!\!\!\!\!#1}}}
%=====================e-mail==================================================
\newcommand{\theemail}{}
\newcommand{\email}[2]{%
   \renewcommand{\theemail}{%
           \noindent {#1 #2}}}
%==============================abstract========================================
\newcommand{\theworkabstract}{}
\newcommand{\workabstract}[1]{%
   \renewcommand{\theworkabstract}{\noindent \ignorespaces #1}}
%===============================engabstract=====================================
\newcommand{\theengabstract}{}
\newcommand{\engabstract}[1]{%
   \renewcommand{\theengabstract}{\noindent \ignorespaces  #1}}
%=========================keywords==============================================
\newcommand{\thekeywords}{}
\renewcommand{\keywords}[1]{%
           \renewcommand{\thekeywords}{\noindent \vskip2mm  #1}}
%==========================thekeywords==========================================
\newcommand{\theengkeywords}{}
\newcommand{\engkeywords}[1]{%
           \renewcommand{\theengkeywords}{\noindent \vskip2mm  #1}}
%==================udk==========================================================
\newcommand{\theudk}{}
\newcommand{\udk}[1]{%
   \renewcommand{\theudk}{{\noindent\ignorespaces\normalsize #1}}}

%===============================msc===============================================
\newcommand{\themsc}{}
\newcommand{\msc}[1]{%
   \renewcommand{\themsc}{{\noindent \ignorespaces\normalsize #1}}}
%=================================================================================
\newcommand{\firstpage}{}
\newcommand{\lastpage}{}
%==========================================================
\newcommand{\thePartit}{}
\newcommand{\Partit}[1]{\renewcommand{\thePartit}{\LARGE #1}}
%===========================bibliography===========================================
\newcounter{N}
\renewenvironment{thebibliography}[1]%
                 {\vskip5mm%
                  \normalfont\footnotesize%
                  {\hspace{-1.5em}\large\sffamily Библиографический список}%
                  {\vskip5mm}
                  \begin{list}{\arabic{N}.}{%
                  \usecounter{N}}}%
                 {\end{list}}
                 
%=====================================================
%\newcounter{table}\addtocounter{table}{1}
%\newcommand{\captiontable}[1]
%{{\hspace{33em}\textit{�������}\refstepcounter{table}~\textit{\thetable}} \centering \textbf{#1}}
%=================================================   
%\renewcommand{\caption}[1]{\vskip\small � ис.\refstepcounter{figure}~\thefigure. \centering  #1}        
%=========thanks=======================================================
\renewcommand{\thanks}[1]{\vskip1mm\par\normalsize\normalfont #1}
%======================================================================
\newcommand{\clear}{\setcounter{footnote}{1}\renewcommand{\date}{}\engshortauthor{}}
%============================thedate===================================
%======================================================================
\newcommand{\theengrevdate}{}
\newcommand{\theengdate}{}
\newcommand{\thedate}{}
\newcommand{\revisiondate}{}
\newcommand{\therevdate}{}
\newcommand{\rdata}{}
\newcommand{\engdate}[1]{\renewcommand{\theengdate}{ #1}}
\renewcommand{\rdata}[1]{\vspace{1cm}\rm \footnotesize Поступила в редакцию~/~Original article submitted: #1} 
\renewcommand{\revisiondate}[1]{\vspace{1cm}\rm \footnotesize В окончательном варианте~/~Revision submitted: #1} 
%\newcommand{\engrevisiondate}[1]{\renewcommand{\theengrevdate}{#1}}
  % \renewcommand{\revisiondate}[1]{
  %\renewcommand{\therevdate}{\rm \footnotesize #1}}
%=======define titlepage============================
\newcommand{\thecopyr}{}
\newcommand{\theengcopyr}{}
\newcommand{\rcopyr}[1]{\renewcommand{\thecopyr}{\vspace{0.5cm}\hfill\normalsize\textcopyright~#1,~\MFITyear}} 
\newcommand{\engcopyr}[1]{\renewcommand{\theengcopyr}{\vspace{0.5cm}\hfill\normalsize\textcopyright~#1,~\MFITyear}}
%==================================================
%\renewcommand{\footnote}[1]{\footnotemark{$^{\thefootnote}$} \footnotetext{$^{\thefootnote}$ #1}}
%==========================================define maketitle
\def\tit{\normalsize Вестник~КРАУНЦ.~Физ.-мат. науки. \MFITyear. \No~\MFITnumber(\MFITom). C.~\firstpage-\lastpage. \,\normalsize\ISSN}
%==============================================================
\def\@maketitle{
\newpage
\thispagestyle{plain}
%\clear
\tit
\vspace{0.2em}
\hrule
\vspace{0.3em}
\hrule
\hspace{0.5em}
\begin{center}
\DOI
\end{center}
\begin{center}
\vspace{-0.5em}
\Large\SEC
\end{center}
\vspace{-0.5em}
\small{\theudk}
\begin{center}
\thertitle
\end{center}
\begin{center}
\bf\Large\@author
\end{center}
{\normalsize \institutename \vspace{0.25em}\theemail}
\begin{abstract}
\theworkabstract
\thekeywords
\end{abstract}
\noindent\thecopyr
%\theotherinf
%\par{\footnotesize
%\hfill\thedate\par}
}

%=================================
\newcommand{\engmaketitle}{%
\thispagestyle{plain}
\begin{center}
\vspace*{-1em}
\Large\ESEC
\end{center}
\begin{flushleft}
\vspace*{-0.5em}
\themsc
\end{flushleft}
\begin{center}
\thetitle
\end{center}
\begin{center}
\noindent\theauthor
\end{center}
{\normalsize \enginstitutename \vspace{0.25em}\theemail}
\begin{abstract}
\theengabstract
\theengkeywords
\end{abstract}
\noindent\theengcopyr}
%==========================================================
\newcommand{\cmd}[1]{\texttt{#1}}
\newcommand{\roi}{ROI\_{}PAC}
% Определение окружений
\newenvironment{newthm}[2][s]
{\vskip.5mm \it \ifthenelse{\equal{#1}{s}}{{\small \sc #2.}}{{\small \sc #2 #1.}}}{\vskip.5mm}

\newenvironment{proof}[1][s]
{\vskip.5mm 
\ifthenelse{\equal{#1}{s}}{{\bf Доказательство. }}{{\it \stretchwith{\,}{#1}. }}}{$\square$}

\newenvironment{task}[1][s]
{\vskip.5mm \it \ifthenelse{\equal{#1}{s}}{{\bf Задача. }}
{{\small \bf Задача #1. }}}{}


\newenvironment{theorem}[1][s]
{\vskip.5mm \it \ifthenelse{\equal{#1}{s}}{{\bf Теорема. }}
{{\small \bf Теорема #1. }}}{\vskip.5mm}

\newenvironment{remark}[1][s]
{\smallskip\ifthenelse{\equal{#1}{s}}{{\bf Замечание. }}
{{\small \sc Замечание #1.}}}{\smallskip}


\newenvironment{forexample}[1][s]
{\vskip.5mm \ifthenelse{\equal{#1}{s}}{{\small \sc Пример. }}
{{\small \sc Пример #1. }}}{}

\newenvironment{lemma}[1][s]
{\vskip.5mm \it \ifthenelse{\equal{#1}{s}}{{\small \sc Лемма. }}
{{\small \sc Лемма #1. }}}{}

\newenvironment{definition}[1][s]
{\vskip.5mm \ifthenelse{\equal{#1}{s}}{{\small \sc Определение. }}
{{\small \sc Определение #1. }}}{}

\newenvironment{consequence}[1][s]
{\vskip.5mm \ifthenelse{\equal{#1}{s}}{{\small \sc Следствие. }}
{{\small \sc Следствие #1. }}}{}
%==========================================================
\newenvironment{engproof}[1][s]
{\vskip.5mm 
\ifthenelse{\equal{#1}{s}}{{\bf Proof. }}{{\it \stretchwith{\,}{#1}. }}}{$\square$}

\newenvironment{engtask}[1][s]
{\vskip.5mm \it \ifthenelse{\equal{#1}{s}}{{\bf Problem. }}
{{\small \bf Problem #1. }}}{}


\newenvironment{engtheorem}[1][s]
{\vskip.5mm \it \ifthenelse{\equal{#1}{s}}{{\bf Theorem. }}
{{\small \bf Theorem #1. }}}{\vskip.5mm}

\newenvironment{engremark}[1][s]
{\smallskip\ifthenelse{\equal{#1}{s}}{{\bf Remark. }}
{{\small \sc Remark #1.}}}{\smallskip}


\newenvironment{engforexample}[1][s]
{\vskip.5mm \ifthenelse{\equal{#1}{s}}{{\small \sc Example. }}
{{\small \sc Example #1. }}}{}

\newenvironment{englemma}[1][s]
{\vskip.5mm \it \ifthenelse{\equal{#1}{s}}{{\small \sc Lemma. }}
{{\small \sc Lemma #1. }}}{}

\newenvironment{engdefinition}[1][s]
{\vskip.5mm \ifthenelse{\equal{#1}{s}}{{\small \sc Definition. }}
{{\small \sc Definition #1. }}}{}

\newenvironment{engconsequence}[1][s]
{\vskip.5mm \ifthenelse{\equal{#1}{s}}{{\small \sc Consequence. }}
{{\small \sc Consequence #1. }}}{}
%======================================================================              
\endinput